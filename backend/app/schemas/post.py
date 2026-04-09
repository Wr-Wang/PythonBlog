"""文章：创建/更新体、访客详情与列表项、后台完整行。"""
from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from app.datetime_utils import format_dt_yyyy_mm_dd_hh_mm_ss_fff
from app.schemas.common import datetime_json_shanghai


class PostBase(BaseModel):
    """写文章时的公共字段（含分类、标签、封面）。"""

    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    excerpt: str | None = Field(None, max_length=500)
    content: str = Field(min_length=1)
    published: bool = False
    category_id: int | None = None
    cover_image_url: str | None = Field(None, max_length=512)
    tag_ids: list[int] = Field(default_factory=list)


class PostCreate(PostBase):
    """POST /api/posts 请求体。"""

    pass


class PostUpdate(BaseModel):
    """PATCH：字段均可选；tag_ids 传 [] 可清空标签。"""

    title: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, min_length=1, max_length=255)
    excerpt: str | None = None
    content: str | None = None
    published: bool | None = None
    category_id: int | None = None
    cover_image_url: str | None = Field(None, max_length=512)
    tag_ids: list[int] | None = None


class PostOut(BaseModel):
    """访客文章详情。"""

    model_config = {"from_attributes": True}

    id: int
    title: str
    slug: str
    excerpt: str | None
    content: str
    published: bool
    cover_image_url: str | None
    created_at: datetime
    updated_at: datetime
    author_id: int | None
    category_id: int | None

    @field_serializer("created_at", "updated_at", when_used="json")
    def _ser_dt_json(self, dt: datetime) -> str:
        return datetime_json_shanghai(dt)


class PostListItem(BaseModel):
    """访客列表项（无正文）。"""

    model_config = {"from_attributes": True}

    id: int
    title: str
    slug: str
    excerpt: str | None
    published: bool
    cover_image_url: str | None
    created_at: datetime
    category_id: int | None

    @field_serializer("created_at", when_used="json")
    def _ser_created_json(self, dt: datetime) -> str:
        return datetime_json_shanghai(dt)


class PostAdminOut(BaseModel):
    """后台文章行：含分类名、tag_ids，时间为 yyyy-MM-dd HH:mm:ss.fff。"""

    model_config = {"from_attributes": True}

    id: int
    title: str
    slug: str
    excerpt: str | None
    content: str
    published: bool
    cover_image_url: str | None
    created_at: datetime
    updated_at: datetime
    author_id: int | None
    author_name: str | None = Field(
        None, description="文章作者登录名，用于后台评论表单默认昵称等"
    )
    category_id: int | None
    category_name: str | None = None
    tag_ids: list[int] = Field(default_factory=list)

    @field_serializer("created_at", "updated_at", when_used="json")
    def _ser_dt(self, dt: datetime) -> str:
        return format_dt_yyyy_mm_dd_hh_mm_ss_fff(dt)
