"""
启动时对已有库做轻量结构补丁（SQLAlchemy create_all 不会给已存在表加列）。

语法要点：
- inspect(engine)：反射库中已有表与列名。
- engine.begin()：事务上下文，失败自动回滚。
"""
import logging
from sqlalchemy import inspect, text  # 第三方：反射与原始 SQL
from sqlalchemy.engine import Engine  # 第三方：引擎类型

logger = logging.getLogger("uvicorn.error")


def _sql_quote_ident(name: str) -> str:
    """SQL Server 用 [name] 包裹标识符。"""
    return "[" + name.replace("]", "]]") + "]"


def _pick_sc_collation(conn, base_collation: str | None) -> str | None:
    """
    从当前排序规则推导支持补充字符的 _SC 规则。
    例：Chinese_PRC_CI_AS -> Chinese_PRC_100_CI_AS_SC（若实例支持）。
    """
    if not base_collation:
        return None
    c = base_collation.strip()
    if not c:
        return None
    if c.upper().endswith("_SC"):
        return c
    candidates: list[str] = []
    # 先尝试基于当前规则推导
    if "_100_" in c:
        candidates.append(c + "_SC")
    elif c.upper() == "CHINESE_PRC_CI_AS":
        candidates.extend(["Chinese_PRC_140_CI_AS_SC", "Chinese_PRC_100_CI_AS_SC"])
    else:
        candidates.append(c + "_SC")
    # 再尝试通用候选
    candidates.extend(
        [
            "Chinese_PRC_140_CI_AS_SC",
            "Chinese_PRC_100_CI_AS_SC",
            "Latin1_General_140_CI_AS_SC",
            "Latin1_General_100_CI_AS_SC",
        ]
    )
    # 去重保序
    uniq: list[str] = []
    for x in candidates:
        if x not in uniq:
            uniq.append(x)
    for cand in uniq:
        ok = conn.execute(
            text("SELECT 1 FROM sys.fn_helpcollations() WHERE name = :name"),
            {"name": cand},
        ).fetchone()
        if ok:
            return cand
    return None


def ensure_comments_unicode_columns(engine: Engine) -> None:
    """
    旧库若 comments.content / author_name 为 VARCHAR/NTEXT 等，存 emoji 会变成 ?。
    改为 NVARCHAR(MAX) / NVARCHAR(128)；已损坏数据无法恢复，需重新发表。

    用 INFORMATION_SCHEMA 判断类型，避免仅依赖 sys.types + user_type_id 时漏检。
    """
    if engine.dialect.name != "mssql":
        return
    insp = inspect(engine)
    try:
        table_names = {t.lower() for t in insp.get_table_names(schema="dbo")}
    except TypeError:
        table_names = {t.lower() for t in insp.get_table_names()}
    if "comments" not in table_names:
        return

    def _pick_content_row(rows):
        if not rows:
            return None
        return next((r for r in rows if r[0].lower() == "dbo"), rows[0])

    def _needs_content_fix(data_type: str | None, maxlen: int | None) -> bool:
        if not data_type:
            return False
        dt = data_type.lower()
        if dt in ("varchar", "char", "text", "ntext"):
            return True
        return False

    def _needs_author_fix(data_type: str | None, maxlen: int | None) -> bool:
        if not data_type:
            return False
        dt = data_type.lower()
        if dt in ("varchar", "char", "text", "ntext"):
            return True
        if dt == "nvarchar" and maxlen is not None and maxlen != -1 and maxlen < 128:
            return True
        return False

    with engine.begin() as conn:
        db_collation = conn.execute(
            text("SELECT CAST(DATABASEPROPERTYEX(DB_NAME(), 'Collation') AS NVARCHAR(200))")
        ).scalar_one_or_none()
        target_sc_collation = _pick_sc_collation(conn, db_collation)

        rows = conn.execute(
            text(
                """
                SELECT TABLE_SCHEMA, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, COLLATION_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = N'comments' AND COLUMN_NAME = N'content'
                """
            )
        ).fetchall()
        row = _pick_content_row(rows)
        if row is not None:
            schema, data_type, maxlen, collation_name = row[0], row[1], row[2], row[3]
            apply_sc = (
                bool(target_sc_collation)
                and isinstance(collation_name, str)
                and not collation_name.upper().endswith("_SC")
            )
            collate_sql = f" COLLATE {target_sc_collation}" if apply_sc else ""
            if _needs_content_fix(data_type, maxlen):
                sch = _sql_quote_ident(schema)
                tbl = _sql_quote_ident("comments")
                col = _sql_quote_ident("content")
                stmt = f"ALTER TABLE {sch}.{tbl} ALTER COLUMN {col} NVARCHAR(MAX){collate_sql} NOT NULL"
                logger.info("comments.content 非 Unicode 宽列，执行: %s", stmt)
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    logger.warning("设置 comments.content 排序规则失败，跳过: %s", e)
            elif apply_sc:
                sch = _sql_quote_ident(schema)
                tbl = _sql_quote_ident("comments")
                col = _sql_quote_ident("content")
                stmt = f"ALTER TABLE {sch}.{tbl} ALTER COLUMN {col} NVARCHAR(MAX) COLLATE {target_sc_collation} NOT NULL"
                logger.info("comments.content 排序规则不支持补充字符，执行: %s", stmt)
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    logger.warning("设置 comments.content 排序规则失败，跳过: %s", e)

        rows2 = conn.execute(
            text(
                """
                SELECT TABLE_SCHEMA, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, COLLATION_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = N'comments' AND COLUMN_NAME = N'author_name'
                """
            )
        ).fetchall()
        row2 = _pick_content_row(rows2)
        if row2 is not None:
            schema, data_type, maxlen, collation_name = row2[0], row2[1], row2[2], row2[3]
            apply_sc = (
                bool(target_sc_collation)
                and isinstance(collation_name, str)
                and not collation_name.upper().endswith("_SC")
            )
            collate_sql = f" COLLATE {target_sc_collation}" if apply_sc else ""
            if _needs_author_fix(data_type, maxlen):
                sch = _sql_quote_ident(schema)
                tbl = _sql_quote_ident("comments")
                col = _sql_quote_ident("author_name")
                stmt = f"ALTER TABLE {sch}.{tbl} ALTER COLUMN {col} NVARCHAR(128){collate_sql} NOT NULL"
                logger.info("comments.author_name 非Unicode，执行: %s", stmt)
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    logger.warning("设置 comments.author_name 排序规则失败，跳过: %s", e)
            elif apply_sc:
                sch = _sql_quote_ident(schema)
                tbl = _sql_quote_ident("comments")
                col = _sql_quote_ident("author_name")
                stmt = f"ALTER TABLE {sch}.{tbl} ALTER COLUMN {col} NVARCHAR(128) COLLATE {target_sc_collation} NOT NULL"
                logger.info("comments.author_name 排序规则不支持补充字符，执行: %s", stmt)
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    logger.warning("设置 comments.author_name 排序规则失败，跳过: %s", e)

        # 与 sys.types 对照的备用（若 INFORMATION_SCHEMA 漏检）
        for sql in (
            """
            IF EXISTS (
                SELECT 1 FROM sys.columns c
                INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
                WHERE c.object_id = OBJECT_ID(N'dbo.comments') AND c.name = N'content'
                  AND t.name IN (N'varchar', N'char', N'text', N'ntext')
            )
            ALTER TABLE dbo.comments ALTER COLUMN content NVARCHAR(MAX) NOT NULL;
            """,
            """
            IF EXISTS (
                SELECT 1 FROM sys.columns c
                INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
                WHERE c.object_id = OBJECT_ID(N'dbo.comments') AND c.name = N'author_name'
                  AND t.name IN (N'varchar', N'char', N'text', N'ntext')
            )
            ALTER TABLE dbo.comments ALTER COLUMN author_name NVARCHAR(128) NOT NULL;
            """,
        ):
            conn.execute(text(sql))


def ensure_comment_status_column(engine: Engine) -> None:
    """为 comments 增加 status（MOD-01）；旧数据默认已审核通过。"""
    if engine.dialect.name != "mssql":
        return
    insp = inspect(engine)
    try:
        table_names = {t.lower() for t in insp.get_table_names(schema="dbo")}
    except TypeError:
        table_names = {t.lower() for t in insp.get_table_names()}
    if "comments" not in table_names:
        return
    try:
        columns = insp.get_columns("comments", schema="dbo")
    except Exception:
        columns = insp.get_columns("comments")
    col_names = {c["name"].lower() for c in columns}
    if "status" in col_names:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE dbo.comments ADD status NVARCHAR(20) NOT NULL "
                "DEFAULT N'approved'"
            )
        )


def ensure_posts_extra_columns(engine: Engine) -> None:
    """为旧版 posts 表补充 category_id、cover_image_url（若缺失）。"""
    insp = inspect(engine)
    # SQL Server 默认架构 dbo；部分环境下 get_table_names() 不含 schema，显式传入更稳
    try:
        table_names = {t.lower() for t in insp.get_table_names(schema="dbo")}
    except TypeError:
        table_names = {t.lower() for t in insp.get_table_names()}
    if "posts" not in table_names:
        return
    try:
        columns = insp.get_columns("posts", schema="dbo")
    except Exception:
        columns = insp.get_columns("posts")
    col_names = {c["name"].lower() for c in columns}
    stmts: list[str] = []
    if "category_id" not in col_names:
        stmts.append("ALTER TABLE posts ADD category_id INT NULL")
    if "cover_image_url" not in col_names:
        stmts.append("ALTER TABLE posts ADD cover_image_url NVARCHAR(512) NULL")
    if "review_status" not in col_names:
        stmts.append("ALTER TABLE posts ADD review_status NVARCHAR(20) NOT NULL DEFAULT N'draft'")
    if "favorite_count" not in col_names:
        stmts.append("ALTER TABLE posts ADD favorite_count INT NOT NULL DEFAULT 0")
    if "like_count" not in col_names:
        stmts.append("ALTER TABLE posts ADD like_count INT NOT NULL DEFAULT 0")
    if "view_count" not in col_names:
        stmts.append("ALTER TABLE posts ADD view_count INT NOT NULL DEFAULT 0")
    if "share_count" not in col_names:
        stmts.append("ALTER TABLE posts ADD share_count INT NOT NULL DEFAULT 0")
    if "rank_level" not in col_names:
        stmts.append("ALTER TABLE posts ADD rank_level INT NOT NULL DEFAULT 1")
    if "weight" not in col_names:
        stmts.append("ALTER TABLE posts ADD weight INT NOT NULL DEFAULT 0")
    if "hot_score" not in col_names:
        stmts.append("ALTER TABLE posts ADD hot_score INT NOT NULL DEFAULT 0")
    if "is_featured" not in col_names:
        stmts.append("ALTER TABLE posts ADD is_featured BIT NOT NULL DEFAULT 0")
    if "is_pinned" not in col_names:
        stmts.append("ALTER TABLE posts ADD is_pinned BIT NOT NULL DEFAULT 0")
    if "published_at" not in col_names:
        stmts.append("ALTER TABLE posts ADD published_at DATETIME NULL")
    if "offline_at" not in col_names:
        stmts.append("ALTER TABLE posts ADD offline_at DATETIME NULL")
    if "content_type" not in col_names:
        stmts.append("ALTER TABLE posts ADD content_type NVARCHAR(20) NULL")
    if "source_url" not in col_names:
        stmts.append("ALTER TABLE posts ADD source_url NVARCHAR(512) NULL")
    if not stmts:
        return
    with engine.begin() as conn:
        for sql in stmts:
            conn.execute(text(sql))
        # 外键：仅当 categories 表存在且尚未有同名约束时尝试（忽略失败由 DBA 处理）
        if "category_id" not in col_names and "categories" in table_names:
            try:
                conn.execute(
                    text(
                        "IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_posts_category_id') "
                        "ALTER TABLE posts ADD CONSTRAINT FK_posts_category_id "
                        "FOREIGN KEY (category_id) REFERENCES categories(id)"
                    )
                )
            except Exception:
                pass


def ensure_roles_data_scope_column(engine: Engine) -> None:
    """为旧版 roles 表补 data_scope（all/self）。"""
    insp = inspect(engine)
    try:
        table_names = {t.lower() for t in insp.get_table_names(schema="dbo")}
    except TypeError:
        table_names = {t.lower() for t in insp.get_table_names()}
    if "roles" not in table_names:
        return
    try:
        columns = insp.get_columns("roles", schema="dbo")
    except Exception:
        columns = insp.get_columns("roles")
    col_names = {c["name"].lower() for c in columns}
    if "data_scope" in col_names:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE roles ADD data_scope NVARCHAR(20) NOT NULL DEFAULT N'all'"))

