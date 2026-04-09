"""
前端 SPA 静态资源挂载：与 API、/docs、/uploads 共存时不抢 Swagger 路由。

策略：
- 仅 mount /assets 到 Vite 构建目录；
- / 与 /{path} 用 FileResponse：真实文件则返回，否则回退 index.html（Vue Router history）。
"""
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("uvicorn.error")


def mount_frontend_dist(app: FastAPI, dist_dir: Path) -> None:
    """
    dist_dir：前端 npm run build 输出目录（含 index.html 与 assets/）。
    """
    dist_dir = dist_dir.resolve()
    if not dist_dir.is_dir():
        return

    assets = dist_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="vite_assets")

    @app.get("/", include_in_schema=False)
    async def spa_root():
        return FileResponse(dist_dir / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        target = (dist_dir / full_path).resolve()
        try:
            target.relative_to(dist_dir)
        except ValueError:
            raise HTTPException(status_code=404)
        if target.is_file():
            return FileResponse(target)
        return FileResponse(dist_dir / "index.html")

    logger.info("已挂载前端 SPA（/assets + index 回退）: %s", dist_dir)
