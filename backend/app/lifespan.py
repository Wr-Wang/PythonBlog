"""
应用生命周期（lifespan）：启动时建库、初始化数据、准备上传目录；供 main 中 FastAPI(lifespan=...) 引用。
"""
import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.config import settings
from app.db_bootstrap import ensure_sql_server_database
from app.database import SessionLocal
from app.db_init import init_db
from app.services.post_scheduler import run_due_post_jobs

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
        db = SessionLocal()
        try:
            run_due_post_jobs(db)  # 启动补偿执行一次
        finally:
            db.close()
        app.state.db_ready = True
        logger.info("数据库初始化成功")
    except Exception as e:
        app.state.db_error = repr(e)
        logger.exception(
            "数据库初始化失败，接口仍可访问 /api/health 查看原因。"
            "请检查 SQL Server、ODBC 与 backend/.env 中的 DATABASE_URL。"
        )
    stop_event = asyncio.Event()

    async def _scheduler_loop():
        while not stop_event.is_set():
            db = SessionLocal()
            try:
                run_due_post_jobs(db)
            except Exception:
                logger.exception("定时上下线任务执行失败")
            finally:
                db.close()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=30.0)
            except TimeoutError:
                pass

    task = asyncio.create_task(_scheduler_loop())
    try:
        yield
    finally:
        stop_event.set()
        task.cancel()
