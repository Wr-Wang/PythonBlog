"""评论：访客展示与发表、后台管理与回复。"""
import base64
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_serializer, model_validator

from app.datetime_utils import format_dt_yyyy_mm_dd_hh_mm_ss_fff
from app.schemas.common import datetime_json_shanghai

_MAX_COMMENT_CHARS = 100_000


def _decode_content_b64(b64: str | None) -> str | None:
    """标准 Base64（UTF-8 字节）；失败或空则返回 None。"""
    if b64 is None or not str(b64).strip():
        return None
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception as e:
        raise ValueError("content_b64 不是合法 Base64") from e
    return raw.decode("utf-8")


def _resolve_comment_content(content: str | None, content_b64: str | None, *, required: bool) -> str | None:
    """
    统一处理评论正文：
    - 若传 content_b64，则优先解码覆盖 content；
    - required=True 时要求非空正文；
    - 全部路径统一做长度限制。
    """
    resolved = content
    if content_b64 and content_b64.strip():
        resolved = _decode_content_b64(content_b64)
    if required and (resolved is None or not resolved.strip()):
        raise ValueError("请填写评论内容")
    if resolved is not None and len(resolved) > _MAX_COMMENT_CHARS:
        raise ValueError("评论内容过长")
    return resolved


class CommentPublicOut(BaseModel):
    """文章下评论列表（公开）。"""

    model_config = {"from_attributes": True}

    id: int
    post_id: int
    parent_id: int | None
    author_name: str
    content: str
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def _ser_created(self, dt: datetime) -> str:
        return datetime_json_shanghai(dt)


class CommentCreatePublic(BaseModel):
    """访客发表评论/回复。"""

    author_name: str = Field(min_length=1, max_length=128)
    content: str | None = None
    """正文；与 content_b64 二选一或同时传（服务端优先使用 content_b64）。"""
    content_b64: str | None = None
    """UTF-8 字节的 Base64，避免部分代理/IIS 链路损坏纯表情 JSON。"""
    parent_id: int | None = None

    @model_validator(mode="after")
    def _resolve_content_public(self):
        self.content = _resolve_comment_content(self.content, self.content_b64, required=True)
        return self


CommentStatus = Literal["pending", "approved", "rejected"]


class CommentAdminOut(BaseModel):
    """后台列表行：附带文章标题。"""

    model_config = {"from_attributes": True}

    id: int
    post_id: int
    post_title: str
    parent_id: int | None
    author_name: str
    content: str
    status: str = "approved"
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def _ser_created(self, dt: datetime) -> str:
        return format_dt_yyyy_mm_dd_hh_mm_ss_fff(dt)


class CommentAdminCreate(BaseModel):
    """后台人工录入评论或回复。"""

    post_id: int
    parent_id: int | None = None
    author_name: str = Field(min_length=1, max_length=128)
    content: str | None = None
    content_b64: str | None = None
    status: CommentStatus = "approved"

    @model_validator(mode="after")
    def _resolve_content_admin_create(self):
        self.content = _resolve_comment_content(self.content, self.content_b64, required=True)
        return self


class CommentAdminUpdate(BaseModel):
    """后台修改昵称或正文。"""

    author_name: str | None = Field(None, min_length=1, max_length=128)
    content: str | None = None
    content_b64: str | None = None
    status: CommentStatus | None = None

    @model_validator(mode="after")
    def _resolve_content_admin_update(self):
        self.content = _resolve_comment_content(self.content, self.content_b64, required=False)
        return self
