"""社区关系模型：作者关注。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, NVARCHAR, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.datetime_utils import now_shanghai_naive


class AuthorFollow(Base):
    __tablename__ = "author_follows"
    __table_args__ = (UniqueConstraint("user_key", "author_id", name="UQ_author_follows_user_author"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_key: Mapped[str] = mapped_column(NVARCHAR(128), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)
