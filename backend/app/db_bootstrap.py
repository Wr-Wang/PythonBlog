"""
启动时在 SQL Server master 上确保业务库存在。

语法要点：
- sqlalchemy.engine.url.make_url：把连接字符串解析为 URL 对象，可改 database 段。
- create_engine(..., isolation_level="AUTOCOMMIT")：DDL 不能包在事务里，需自动提交。
- text()：原始 SQL，配合 Session.execute / Connection.execute。
"""
import logging  # 标准库
import re  # 标准库：正则校验库名

from sqlalchemy import create_engine, text  # 第三方：引擎与 SQL 封装
from sqlalchemy.engine.url import make_url  # 第三方：URL 解析

logger = logging.getLogger("uvicorn.error")

_DB_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,127}$")  # 合法 SQL Server 标识符简化规则


def ensure_sql_server_database(database_url: str) -> None:
    """
    若 URL 中库名非 master 且不存在，则 CREATE DATABASE。
    失败仅打日志，不阻塞应用启动（由 init_db 再决定是否连得上）。
    """
    try:
        u = make_url(database_url)  # 解析 mssql+pyodbc://...
    except Exception as e:
        logger.debug("建库跳过（URL 无法解析）: %s", e)
        return

    db_name = u.database  # URL 路径段即库名
    if not db_name or db_name.lower() == "master":  # 连 master 则不建库
        return

    if not _DB_NAME_RE.match(db_name):  # 防 SQL 注入，限制字符集
        logger.warning("库名不合法，跳过自动建库: %s", db_name)
        return

    master_url = u.set(database="master")  # 克隆 URL 只改库名为 master
    engine = create_engine(
        master_url,
        isolation_level="AUTOCOMMIT",  # CREATE DATABASE 要求
        pool_pre_ping=True,
    )
    safe_bracket = db_name.replace("]", "]]")  # T-SQL 转义 ] 为 ]]
    sql = (
        f"IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = N'{db_name}') "
        f"CREATE DATABASE [{safe_bracket}]"
    )

    try:
        with engine.connect() as conn:  # 上下文管理自动关闭连接
            conn.execute(text(sql))  # 执行 DDL
        logger.info("已检查/创建数据库: %s", db_name)
    except Exception as e:
        logger.warning("自动建库失败，可在 SSMS 中执行 database/init.sql。原因: %s", e)
