"""
Pydantic 模式包：按领域拆文件，此处聚合导出，保持 `from app.schemas import PostOut` 不变。
"""
from app.schemas.category import CategoryAdminOut, CategoryCreate, CategoryUpdate
from app.schemas.comment import (
    CommentAdminCreate,
    CommentAdminOut,
    CommentAdminUpdate,
    CommentCreatePublic,
    CommentPublicOut,
)
from app.schemas.post import (
    PostAdminOut,
    PostCreate,
    PostListItem,
    PostOut,
    PostUpdate,
)
from app.schemas.tag import TagAdminOut, TagCreate, TagUpdate
from app.schemas.token import Token
from app.schemas.upload import UploadImageResponse
from app.schemas.user import UserAdminCreate, UserAdminOut, UserAdminUpdate, UserOut

__all__ = [
    "CategoryAdminOut",
    "CategoryCreate",
    "CategoryUpdate",
    "CommentAdminCreate",
    "CommentAdminOut",
    "CommentAdminUpdate",
    "CommentCreatePublic",
    "CommentPublicOut",
    "PostAdminOut",
    "PostCreate",
    "PostListItem",
    "PostOut",
    "PostUpdate",
    "TagAdminOut",
    "TagCreate",
    "TagUpdate",
    "Token",
    "UploadImageResponse",
    "UserAdminCreate",
    "UserAdminOut",
    "UserAdminUpdate",
    "UserOut",
]
