"""通用分页响应：{ items, total }。"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    total: int = Field(ge=0, description="总条数（与 skip/limit 无关）")
