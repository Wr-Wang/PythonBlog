"""
标签 ORM：与文章多对多，中间表见 association.post_tags_table。
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.datetime_utils import now_shanghai_naive
from app.models.association import post_tags_table


class Tag(Base):
    """文章标签表。"""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)

    posts: Mapped[list["Post"]] = relationship(
        "Post", secondary=post_tags_table, back_populates="tags"
    )
