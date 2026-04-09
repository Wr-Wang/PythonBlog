"""
分类 ORM：文章可选归属一个分类。

关联：
- posts：反向一对多，由 Post.category_id 指向本表；使用字符串 "Post" 避免循环 import。
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.datetime_utils import now_shanghai_naive


class Category(Base):
    """文章分类表。"""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_shanghai_naive, onupdate=now_shanghai_naive
    )

    # 由 Post.category_rel 的 back_populates 与之对应
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="category_rel")
