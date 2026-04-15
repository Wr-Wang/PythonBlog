"""标签：创建、部分更新、后台列表响应。"""
from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from app.datetime_utils import format_dt_yyyy_mm_dd_hh_mm_ss_fff


class TagCreate(BaseModel):
    """创建标签请求体。"""
    name: str = Field(min_length=1, max_length=64)
    slug: str = Field(min_length=1, max_length=64)


class TagUpdate(BaseModel):
    """更新标签请求体（字段可选）。"""
    name: str | None = Field(None, min_length=1, max_length=64)
    slug: str | None = Field(None, min_length=1, max_length=64)


class TagAdminOut(BaseModel):
    """后台标签列表项。"""
    model_config = {"from_attributes": True}

    id: int
    name: str
    slug: str
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def _ser_created(self, dt: datetime) -> str:
        return format_dt_yyyy_mm_dd_hh_mm_ss_fff(dt)
