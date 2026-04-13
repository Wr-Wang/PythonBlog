"""
评论 ORM：归属某篇文章，可选 parent_id 回复另一条评论。

注意：
- parent_id 指向 comments.id 的外键不使用 ON DELETE CASCADE，避免与 post→comment 的级联在 SQL Server 上形成「多条级联路径」错误。
- 删除父评论前需先处理子评论，或由管理员在应用层处理。
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.datetime_utils import now_shanghai_naive


class Comment(Base):
    """评论表。"""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("comments.id"), nullable=True)
    # 须 NVARCHAR(MAX)：UnicodeText 在 MSSQL 上曾生成 NTEXT，emoji 易异常；显式 NVARCHAR(None)=MAX
    author_name: Mapped[str] = mapped_column(NVARCHAR(128), nullable=False)
    content: Mapped[str] = mapped_column(NVARCHAR(None), nullable=False)
    # pending=待审核；approved=前台可见；rejected=拒绝（MOD-01）
    status: Mapped[str] = mapped_column(NVARCHAR(20), nullable=False, default="approved")
    reject_type: Mapped[str | None] = mapped_column(NVARCHAR(32), nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(NVARCHAR(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)

    post: Mapped["Post"] = relationship("Post", back_populates="comments")
    parent: Mapped["Comment | None"] = relationship(
        "Comment", remote_side=[id], back_populates="replies"
    )
    replies: Mapped[list["Comment"]] = relationship("Comment", back_populates="parent")
