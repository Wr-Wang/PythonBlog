"""
HTTP 中间件：在数据库未成功初始化时，拦截 /api/*（除健康检查）请求，避免未捕获异常变成 500。

说明：
- lifespan 失败时 app.state.db_ready 为 False，此时 ORM 查询通常会抛连接/协议错误；
- 返回 503 + JSON detail，前端 axios 可展示 `response.data.detail`。
"""
import logging

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

logger = logging.getLogger("uvicorn.error")

_DB_UNAVAILABLE_MSG = (
    "数据库未就绪。请启动本机 SQL Server，核对 backend/.env 的 DATABASE_URL，"
    "并打开 GET /api/health 查看 database 字段中的具体错误。"
)


def register_api_db_gate(app: FastAPI) -> None:
    """注册中间件：仅校验以 /api 开头且非 /api/health 的路径。"""

    @app.middleware("http")
    async def api_database_gate(request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api"):
            return await call_next(request)
        if path == "/api/health":
            return await call_next(request)
        if not getattr(request.app.state, "db_ready", False):
            logger.warning("拒绝 API 请求（数据库未就绪）: %s %s", request.method, path)
            return JSONResponse(
                status_code=503,
                content={"detail": _DB_UNAVAILABLE_MSG},
            )
        return await call_next(request)
