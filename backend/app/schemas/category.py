"""文章分类：创建、部分更新、后台列表响应。"""
from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from app.datetime_utils import format_dt_yyyy_mm_dd_hh_mm_ss_fff


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    slug: str = Field(min_length=1, max_length=128)


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    slug: str | None = Field(None, min_length=1, max_length=128)


class CategoryAdminOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at", when_used="json")
    def _ser_dt(self, dt: datetime) -> str:
        return format_dt_yyyy_mm_dd_hh_mm_ss_fff(dt)
