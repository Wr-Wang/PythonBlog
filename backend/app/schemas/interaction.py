"""文章互动与阅读指标 schemas。"""
from datetime import datetime

from pydantic import BaseModel, Field


class PostActionBody(BaseModel):
    user_key: str = Field(min_length=1, max_length=128)


class PostShareBody(BaseModel):
    channel: str = Field(default="link", min_length=1, max_length=32)
    user_key: str | None = Field(default=None, max_length=128)


class PostReportBody(BaseModel):
    reason: str = Field(min_length=1, max_length=64)
    detail: str | None = Field(default=None, max_length=1000)
    user_key: str | None = Field(default=None, max_length=128)


class PostViewBody(BaseModel):
    user_key: str = Field(min_length=1, max_length=128)
    duration_sec: int = Field(default=0, ge=0, le=24 * 3600)
    completed: bool = False


class InteractionStatsOut(BaseModel):
    favorite_count: int
    like_count: int
    view_count: int
    share_count: int
    report_count: int
    hot_score: int


class PostViewMetricsOut(BaseModel):
    today_views: int
    avg_duration_sec: int
    completion_rate: float
    generated_at: datetime
