"""
用户 ORM：后台登录账号。

字段说明：
- hashed_password：仅存 bcrypt 等哈希，永不存明文。
- is_active：False 时 JWT 校验会拒绝，用于软禁用。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.datetime_utils import now_shanghai_naive


class User(Base):
    """用户表。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)
