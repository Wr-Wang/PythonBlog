"""
ORM 模型包：按业务拆分为独立模块，本文件统一导出。

推荐用法：`from app.models import User, Post`（与原先单文件 models.py 一致）。
"""
from app.models.association import post_tags_table
from app.models.category import Category
from app.models.comment import Comment
from app.models.interaction import PostFavorite, PostLike, PostReport, PostShare, PostViewEvent
from app.models.ops import BlacklistWord, FeatureFlag, SearchHotword, SearchSynonym, SensitiveWord
from app.models.post import Post
from app.models.rbac import AuditLog, Menu, Permission, Role, RoleMenu, RolePermission, UserRole
from app.models.tag import Tag
from app.models.user import User

__all__ = [
    "post_tags_table",
    "Category",
    "Comment",
    "PostFavorite",
    "PostLike",
    "PostShare",
    "PostReport",
    "PostViewEvent",
    "FeatureFlag",
    "SensitiveWord",
    "BlacklistWord",
    "SearchSynonym",
    "SearchHotword",
    "Post",
    "Role",
    "Permission",
    "Menu",
    "UserRole",
    "RolePermission",
    "RoleMenu",
    "AuditLog",
    "Tag",
    "User",
]
