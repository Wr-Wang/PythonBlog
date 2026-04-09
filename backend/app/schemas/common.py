"""
Pydantic 公共序列化工具：公开接口用 ISO+东八区，与后台列表格式区分。

说明：
- datetime_json_shanghai：给访客端 PostOut 等使用，便于前端 `new Date(iso)`。
- format_dt_yyyy_mm_dd_hh_mm_ss_fff 定义在 datetime_utils，此处不重复实现。
"""
from datetime import datetime

from app.datetime_utils import TZ_SHANGHAI


def datetime_json_shanghai(dt: datetime) -> str:
    """naive 时间视为东八区墙上时间，补上 tzinfo 后输出 ISO 字符串。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_SHANGHAI)
    return dt.isoformat()
