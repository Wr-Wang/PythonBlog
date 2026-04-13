"""用户：公开摘要、后台管理 CRUD 体与响应。"""
from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from app.datetime_utils import format_dt_yyyy_mm_dd_hh_mm_ss_fff


class UserOut(BaseModel):
    """/auth/me 等：不含密码字段。"""

    id: int
    username: str
    is_active: bool
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    menus: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class UserAdminOut(BaseModel):
    """后台列表：含 hashed_password，时间列为 yyyy-MM-dd HH:mm:ss.fff。"""

    id: int
    username: str
    hashed_password: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("created_at", when_used="json")
    def _ser_created(self, dt: datetime) -> str:
        return format_dt_yyyy_mm_dd_hh_mm_ss_fff(dt)


class UserAdminCreate(BaseModel):
    """后台新建用户。"""

    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    is_active: bool = True


class UserAdminUpdate(BaseModel):
    """后台更新：密码可选（不传则不修改）。"""

    username: str | None = Field(None, min_length=3, max_length=64)
    password: str | None = Field(None, min_length=6, max_length=128)
    is_active: bool | None = None
