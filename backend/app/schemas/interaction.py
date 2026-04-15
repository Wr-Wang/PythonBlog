"""文章互动与阅读指标 schemas。"""
from datetime import datetime

from pydantic import BaseModel, Field


class PostActionBody(BaseModel):
    """点赞/收藏等动作请求体。"""
    user_key: str = Field(min_length=1, max_length=128)


class PostShareBody(BaseModel):
    """分享动作请求体。"""
    channel: str = Field(default="link", min_length=1, max_length=32)
    user_key: str | None = Field(default=None, max_length=128)


class PostReportBody(BaseModel):
    """举报请求体。"""
    reason: str = Field(min_length=1, max_length=64)
    detail: str | None = Field(default=None, max_length=1000)
    user_key: str | None = Field(default=None, max_length=128)


class PostViewBody(BaseModel):
    """浏览上报请求体。"""
    user_key: str = Field(min_length=1, max_length=128)
    duration_sec: int = Field(default=0, ge=0, le=24 * 3600)
    completed: bool = False


class InteractionStatsOut(BaseModel):
    """互动统计响应。"""
    favorite_count: int
    like_count: int
    view_count: int
    share_count: int
    report_count: int
    hot_score: int


class PostViewMetricsOut(BaseModel):
    """阅读质量指标响应。"""
    today_views: int
    avg_duration_sec: int
    completion_rate: float
    generated_at: datetime
