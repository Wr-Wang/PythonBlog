"""文件上传接口的 JSON 响应。"""
from pydantic import BaseModel


class UploadImageResponse(BaseModel):
    """返回浏览器可访问的 url（相对路径 /uploads/...）与存储文件名。"""

    url: str
    filename: str
