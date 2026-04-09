"""认证相关模式：登录返回的 access_token 等。"""
from pydantic import BaseModel


class Token(BaseModel):
    """OAuth2 风格 access_token + token_type。"""

    access_token: str
    token_type: str = "bearer"
