"""
文章互动与行为事件模型：
- 收藏/点赞：唯一键 (post_id, user_key)
- 分享/举报/浏览事件：明细日志，供统计与风控
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, NVARCHAR, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.datetime_utils import now_shanghai_naive


class PostFavorite(Base):
    __tablename__ = "post_favorites"
    __table_args__ = (UniqueConstraint("post_id", "user_key", name="UQ_post_favorites_post_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_key: Mapped[str] = mapped_column(NVARCHAR(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class PostLike(Base):
    __tablename__ = "post_likes"
    __table_args__ = (UniqueConstraint("post_id", "user_key", name="UQ_post_likes_post_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_key: Mapped[str] = mapped_column(NVARCHAR(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class PostShare(Base):
    __tablename__ = "post_shares"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    channel: Mapped[str] = mapped_column(NVARCHAR(32), nullable=False, default="link")
    user_key: Mapped[str | None] = mapped_column(NVARCHAR(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class PostReport(Base):
    __tablename__ = "post_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(NVARCHAR(64), nullable=False)
    detail: Mapped[str | None] = mapped_column(NVARCHAR(1000), nullable=True)
    user_key: Mapped[str | None] = mapped_column(NVARCHAR(128), nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class PostViewEvent(Base):
    __tablename__ = "post_view_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_key: Mapped[str] = mapped_column(NVARCHAR(128), nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)
