"""
SQLAlchemy 引擎与会话（SQL Server）。

语法要点：
- create_engine：创建连接池与方言（由 URL 中 mssql+pyodbc 决定）。
- sessionmaker：工厂函数，每次调用得到新 Session。
- DeclarativeBase：声明式模型基类，子类用 Mapped[] 标注列类型。
- yield：在 get_db 中构成依赖注入用的生成器，finally 保证关闭会话。
"""
from sqlalchemy import create_engine  # 第三方：引擎工厂
from sqlalchemy.orm import DeclarativeBase, sessionmaker  # 第三方：基类与会话工厂

from app.config import settings  # 项目内：读取 DATABASE_URL


def _patch_mssql_pagination_compat() -> None:
    """
    SQLAlchemy 在 SQL Server 2012+ 上会走 OFFSET + FETCH FIRST 分页。
    许多实例（含兼容级别较低或非标准版）对 FETCH FIRST 报错，仅接受 FETCH NEXT 或更老语法。

    做法：在 MSDialect 完成版本检测后强制 _supports_offset_fetch = False，
    走 ROW_NUMBER() 子查询分页（translate_select_structure），不再生成 FETCH 子句。
    比仅替换字符串更稳，且不依赖具体 SQL 片段格式。
    """
    from sqlalchemy.dialects.mssql.base import MSDialect

    _orig = MSDialect._setup_version_attributes

    def _setup_version_attributes(self) -> None:
        _orig(self)
        self._supports_offset_fetch = False

    MSDialect._setup_version_attributes = _setup_version_attributes  # type: ignore[method-assign]


_patch_mssql_pagination_compat()

engine = create_engine(  # 全局单例引擎；多线程下由连接池分配连接
    settings.database_url,  # mssql+pyodbc://...
    pool_pre_ping=True,  # 取连接前 ping，避免用过期连接
    pool_size=5,  # 常驻连接数
    max_overflow=10,  # 超出 pool_size 时临时多开的连接上限
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # 显式控制提交与 flush


class Base(DeclarativeBase):
    """所有 ORM 模型继承此类，以便 create_all 一次建表。"""

    pass  # 无额外字段，仅占位


def get_db():
    """
    FastAPI Depends(get_db) 使用：每次请求 yield 一个 Session，结束关闭。
    生成器语法：yield 之前是准备，之后是清理（此处用 finally 更稳妥）。
    """
    db = SessionLocal()  # 新建会话（非线程安全，勿跨请求复用）
    try:
        yield db  # 交给路由函数使用
    finally:
        db.close()  # 归还连接到池
