"""
博客 API 应用入口：创建 FastAPI 实例、中间件、路由挂载、健康检查与静态资源。

职责划分：
- 数据库与种子数据 → app.db_init + app.lifespan
- 前端 dist 托管 → app.frontend_spa
- 各业务 API → app.routers.*
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.frontend_spa import mount_frontend_dist
from app.http_middleware import register_api_db_gate
from app.lifespan import app_lifespan
from app.routers import auth, categories, comments, posts, tags, upload, users_admin

# backend/app/main.py → 上两级为 backend，再上为项目根 PythonBlog
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_FRONTEND_DIST = _PROJECT_ROOT / "frontend" / "dist"

app = FastAPI(
    title="Personal Blog API",
    lifespan=app_lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS：开发时 Vue 与 API 不同端口需放行
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
_PRIVATE_ORIGIN_RE = (
    r"http://("
    r"localhost|127\.0\.0\.1|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?$"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:5173"],
    allow_origin_regex=_PRIVATE_ORIGIN_RE,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_api_db_gate(app)

app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(categories.router)
app.include_router(tags.router)
app.include_router(users_admin.router)
app.include_router(comments.router)
app.include_router(upload.router)

# 用户上传图片，URL 形如 /uploads/<filename>
_UPLOAD_ROOT = Path(settings.upload_dir).resolve()
_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_UPLOAD_ROOT)), name="blog_uploads")


@app.get("/api/health")
def health():
    """进程存活与数据库初始化是否成功（失败时仍返回 degraded + 错误字符串）。"""
    return {
        "status": "ok" if app.state.db_ready else "degraded",
        "database": "ok" if app.state.db_ready else app.state.db_error,
    }


if not _FRONTEND_DIST.is_dir():

    @app.get("/")
    def root_no_frontend():
        """未构建前端时根路径返回 JSON 指引。"""
        return {
            "message": "后端已启动；尚未构建前端。请在 frontend 目录执行 npm run build，或单独运行 npm run dev 访问开发站点。",
            "swagger_ui": "/docs",
            "openapi_json": "/openapi.json",
            "redoc": "/redoc",
            "health": "/api/health",
        }


if _FRONTEND_DIST.is_dir():
    mount_frontend_dist(app, _FRONTEND_DIST)
