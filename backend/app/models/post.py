"""
文章 ORM：正文、元数据、作者、分类、标签、评论。

说明：
- slug：URL 片段，全局唯一。
- published：访客接口只展示为 True 的文章。
- author 使用 User 的 backref="posts"，故 User 模型内无需再写 relationship。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.datetime_utils import now_shanghai_naive
from app.models.association import post_tags_table
from app.models.comment import Comment
from app.models.tag import Tag


class Post(Base):
    """文章表。"""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    excerpt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    # 工作流：draft/pending/approved/rejected/offline
    review_status: Mapped[str] = mapped_column(String(20), default="draft")
    cover_image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # 增长与排序字段
    favorite_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    rank_level: Mapped[int] = mapped_column(Integer, default=1)
    weight: Mapped[int] = mapped_column(Integer, default=0)
    hot_score: Mapped[int] = mapped_column(Integer, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    offline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_shanghai_naive, onupdate=now_shanghai_naive
    )
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)

    author: Mapped["User | None"] = relationship("User", backref="posts")
    category_rel: Mapped["Category | None"] = relationship("Category", back_populates="posts")
    tags: Mapped[list[Tag]] = relationship(
        "Tag", secondary=post_tags_table, back_populates="posts"
    )
    comments: Mapped[list[Comment]] = relationship(
        "Comment", back_populates="post", cascade="all, delete-orphan"
    )
    column_links: Mapped[list["ColumnPost"]] = relationship(
        "ColumnPost", back_populates="post", cascade="all, delete-orphan"
    )

    @property
    def author_name(self) -> str | None:
        return self.author.username if self.author is not None else None
