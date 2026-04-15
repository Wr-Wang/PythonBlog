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
from app.schemas.column import (
    ColumnAdminOut,
    ColumnCreate,
    ColumnPostBrief,
    ColumnPublicDetailOut,
    ColumnPublicListItem,
    ColumnUpdate,
)
from app.schemas.interaction import (
    InteractionStatsOut,
    PostActionBody,
    PostReportBody,
    PostShareBody,
    PostViewBody,
    PostViewMetricsOut,
)
from app.schemas.page import Page
from app.schemas.post import (
    PostAdminListResponse,
    PostAdminOut,
    PostCreate,
    PostListItem,
    PostOut,
    PostUpdate,
)
from app.schemas.tag import TagAdminOut, TagCreate, TagUpdate
from app.schemas.token import Token
from app.schemas.upload import UploadImageResponse
from app.schemas.rbac import (
    AuditLogOut,
    MenuCreate,
    MenuOut,
    MenuUpdate,
    PermissionBindBody,
    PermissionCreate,
    PermissionOut,
    RoleBindBody,
    RoleCreate,
    RoleOut,
    RoleUpdate,
)
from app.schemas.user import UserAdminCreate, UserAdminOut, UserAdminUpdate, UserOut

__all__ = [
    "Page",
    "CategoryAdminOut",
    "CategoryCreate",
    "CategoryUpdate",
    "CommentAdminCreate",
    "CommentAdminOut",
    "CommentAdminUpdate",
    "CommentCreatePublic",
    "CommentPublicOut",
    "ColumnAdminOut",
    "ColumnCreate",
    "ColumnPostBrief",
    "ColumnPublicDetailOut",
    "ColumnPublicListItem",
    "ColumnUpdate",
    "InteractionStatsOut",
    "PostActionBody",
    "PostShareBody",
    "PostReportBody",
    "PostViewBody",
    "PostViewMetricsOut",
    "PostAdminListResponse",
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
    "RoleOut",
    "RoleCreate",
    "RoleUpdate",
    "RoleBindBody",
    "PermissionOut",
    "PermissionCreate",
    "PermissionBindBody",
    "MenuOut",
    "MenuCreate",
    "MenuUpdate",
    "AuditLogOut",
    "UserAdminCreate",
    "UserAdminOut",
    "UserAdminUpdate",
    "UserOut",
]
