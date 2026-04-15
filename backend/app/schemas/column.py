from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from app.schemas.common import datetime_json_shanghai


class ColumnBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    slug: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    cover_image_url: str | None = Field(default=None, max_length=512)
    is_public: bool = True
    post_ids: list[int] = Field(default_factory=list)


class ColumnCreate(ColumnBase):
    pass


class ColumnUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    slug: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    cover_image_url: str | None = Field(default=None, max_length=512)
    is_public: bool | None = None
    post_ids: list[int] | None = None


class ColumnPostBrief(BaseModel):
    """前台专栏内可见文章（已发布），用于跳转详情。"""

    model_config = {"from_attributes": True}

    id: int
    title: str
    slug: str
    published_at: datetime | None = None
    author_name: str | None = None

    @field_serializer("published_at", when_used="json")
    def _ser_pub(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        return datetime_json_shanghai(dt)


class ColumnPublicListItem(BaseModel):
    """前台专栏列表项。"""

    model_config = {"from_attributes": True}

    id: int
    name: str
    slug: str
    description: str | None
    cover_image_url: str | None
    updated_at: datetime
    visible_post_count: int = 0

    @field_serializer("updated_at", when_used="json")
    def _ser_upd(self, dt: datetime) -> str:
        return datetime_json_shanghai(dt)


class ColumnPublicDetailOut(BaseModel):
    """前台专栏详情：仅包含对访客可见（已发布）的文章，顺序与后台一致。"""

    model_config = {"from_attributes": True}

    id: int
    name: str
    slug: str
    description: str | None
    cover_image_url: str | None
    is_public: bool
    author_id: int | None
    created_at: datetime
    updated_at: datetime
    posts: list[ColumnPostBrief] = Field(default_factory=list)

    @field_serializer("created_at", "updated_at", when_used="json")
    def _ser_dt(self, dt: datetime) -> str:
        return datetime_json_shanghai(dt)


class ColumnAdminOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    slug: str
    description: str | None
    cover_image_url: str | None
    is_public: bool
    author_id: int | None
    created_at: datetime
    updated_at: datetime
    post_ids: list[int] = Field(default_factory=list)
    post_titles: list[str] = Field(default_factory=list)

    @field_serializer("created_at", "updated_at", when_used="json")
    def _ser_dt_json(self, dt: datetime) -> str:
        return datetime_json_shanghai(dt)
