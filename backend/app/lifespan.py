"""
应用生命周期（lifespan）：启动时建库、初始化数据、准备上传目录；供 main 中 FastAPI(lifespan=...) 引用。
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.config import settings
from app.db_bootstrap import ensure_sql_server_database
from app.db_init import init_db

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    yield 之前：连接 SQL Server、创建 BlogDB（若需）、init_db、标记 db_ready。
    yield 之后：当前无清理逻辑；Uvicorn 退出时进程结束。
    """
    app.state.db_ready = False
    app.state.db_error = None
    try:
        ensure_sql_server_database(settings.database_url)
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
        init_db()
        app.state.db_ready = True
        logger.info("数据库初始化成功")
    except Exception as e:
        app.state.db_error = repr(e)
        logger.exception(
            "数据库初始化失败，接口仍可访问 /api/health 查看原因。"
            "请检查 SQL Server、ODBC 与 backend/.env 中的 DATABASE_URL。"
        )
    yield
