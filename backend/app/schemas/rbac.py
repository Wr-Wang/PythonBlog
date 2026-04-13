"""RBAC / 菜单 / 审计相关 schemas。"""
from datetime import datetime

from pydantic import BaseModel, Field


class RoleOut(BaseModel):
    id: int
    code: str
    name: str
    data_scope: str
    is_active: bool

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    data_scope: str = Field(default="all", max_length=20)
    is_active: bool = True


class RoleUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=64)
    data_scope: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None


class PermissionOut(BaseModel):
    id: int
    code: str
    name: str

    model_config = {"from_attributes": True}


class PermissionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)


class MenuOut(BaseModel):
    id: int
    code: str
    name: str
    route: str
    icon: str | None
    order_no: int
    hidden: bool

    model_config = {"from_attributes": True}


class MenuCreate(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=64)
    route: str = Field(min_length=1, max_length=256)
    icon: str | None = Field(default=None, max_length=64)
    order_no: int = 0
    hidden: bool = False


class MenuUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=128)
    name: str | None = Field(default=None, min_length=1, max_length=64)
    route: str | None = Field(default=None, min_length=1, max_length=256)
    icon: str | None = Field(default=None, max_length=64)
    order_no: int | None = None
    hidden: bool | None = None


class RoleBindBody(BaseModel):
    role_ids: list[int] = Field(default_factory=list)


class PermissionBindBody(BaseModel):
    permission_ids: list[int] = Field(default_factory=list)
    menu_ids: list[int] = Field(default_factory=list)


class UserRoleBindingsOut(BaseModel):
    user_id: int
    role_ids: list[int] = Field(default_factory=list)


class RoleBindingsOut(BaseModel):
    role_id: int
    permission_ids: list[int] = Field(default_factory=list)
    menu_ids: list[int] = Field(default_factory=list)


class AuditLogOut(BaseModel):
    id: int
    actor_user_id: int | None
    action: str
    target_type: str
    target_id: str
    detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
