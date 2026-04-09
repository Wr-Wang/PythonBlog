"""
文章与标签的多对多关联表定义。

说明：
- 使用 sqlalchemy.Table 而非 ORM 类：中间表仅保存外键，无单独业务字段。
- ondelete=CASCADE：删除文章或标签时自动清理关联行。
"""
from sqlalchemy import Column, ForeignKey, Integer, Table  # 列与外键

from app.database import Base  # 与所有模型共用同一 metadata

# 表名 post_tags；复合主键 (post_id, tag_id)
post_tags_table = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)
