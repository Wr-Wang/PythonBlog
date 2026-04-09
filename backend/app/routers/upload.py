"""
图片上传 HTTP 路由：multipart 文件写入 settings.upload_dir，返回相对 URL。

main.py 将 upload_dir 挂载到 /uploads；前端开发环境需代理 /uploads。
"""
import uuid
from pathlib import Path
from typing import Annotated

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import settings
from app.deps import get_current_user
from app.rate_limit import require_rate_limit_upload_image
from app.models import User
from app.schemas import UploadImageResponse

router = APIRouter(prefix="/api/upload", tags=["upload"])

_ALLOWED = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_EXT = {".jpg": ".jpg", ".jpeg": ".jpg", ".png": ".png", ".gif": ".gif", ".webp": ".webp"}


@router.post("/image", response_model=UploadImageResponse)
async def upload_image(
    _: Annotated[None, Depends(require_rate_limit_upload_image)],
    current: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    if not file.content_type or file.content_type not in _ALLOWED:
        raise HTTPException(status_code=400, detail="仅支持 jpeg/png/gif/webp")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件超过 5MB")
    suffix = Path(file.filename or "").suffix.lower()
    ext = _EXT.get(suffix, ".bin")
    if ext == ".bin":
        if file.content_type == "image/jpeg":
            ext = ".jpg"
        elif file.content_type == "image/png":
            ext = ".png"
        elif file.content_type == "image/gif":
            ext = ".gif"
        else:
            ext = ".webp"
    name = f"{uuid.uuid4().hex}{ext}"
    root = Path(settings.upload_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    dest = root / name
    dest.write_bytes(raw)
    url = f"/uploads/{name}"
    return UploadImageResponse(url=url, filename=name)
