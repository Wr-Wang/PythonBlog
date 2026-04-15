"""专栏模型：专栏与文章多对多关联（带排序）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.datetime_utils import now_shanghai_naive


class ColumnPost(Base):
    """专栏-文章关联表，sort_order 表示专栏内展示顺序（升序）。"""

    __tablename__ = "column_posts"

    column_id: Mapped[int] = mapped_column(ForeignKey("columns.id", ondelete="CASCADE"), primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    column: Mapped["ColumnModel"] = relationship("ColumnModel", back_populates="post_links")
    post: Mapped["Post"] = relationship("Post", back_populates="column_links")


class ColumnModel(Base):
    __tablename__ = "columns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(NVARCHAR(128), nullable=False)
    slug: Mapped[str] = mapped_column(NVARCHAR(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(NVARCHAR(500), nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(NVARCHAR(512), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_shanghai_naive, onupdate=now_shanghai_naive
    )

    post_links: Mapped[list[ColumnPost]] = relationship(
        "ColumnPost",
        back_populates="column",
        cascade="all, delete-orphan",
        order_by="ColumnPost.sort_order",
    )
