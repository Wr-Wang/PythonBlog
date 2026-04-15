"""
API 速率限制（SEC-01）：按客户端 IP 滑动窗口计数，超限返回 429。

单进程内存实现；多实例部署时需在网关或 Redis 层做一致限流（见需求 §4）。
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from fastapi import HTTPException, Request, status


def get_remote_address(request: Request) -> str:
    """与 slowapi 类似：取直连客户端 IP；若前接反向代理可后续扩展 X-Forwarded-For。"""
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


class _SlidingWindowLimiter:
    """每个 key 在 window_seconds 内最多允许 limit 次。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            arr = self._hits[key]
            arr[:] = [t for t in arr if t > cutoff]
            if len(arr) >= limit:
                return False
            arr.append(now)
            return True


_limiter = _SlidingWindowLimiter()

# 与需求 SEC-01 对应的默认配额（可按后续配置项外移）
LIMIT_LOGIN_PER_MIN = 10
LIMIT_AUTH_CAPTCHA_PER_MIN = 40
LIMIT_COMMENT_PUBLIC_PER_MIN = 30
LIMIT_UPLOAD_IMAGE_PER_MIN = 30


class RateLimit:
    """可作为 Depends(RateLimit(...)) 使用。"""

    def __init__(self, limit: int, window_seconds: int, route_key: str) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.route_key = route_key

    def __call__(self, request: Request) -> None:
        ip = get_remote_address(request)
        key = f"{self.route_key}:{ip}"
        if not _limiter.allow(key, self.limit, self.window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试",
            )


# 预置依赖（每分钟 = 60 秒窗口）
rate_limit_login = RateLimit(LIMIT_LOGIN_PER_MIN, 60, "auth_login")
rate_limit_auth_captcha = RateLimit(LIMIT_AUTH_CAPTCHA_PER_MIN, 60, "auth_captcha")
rate_limit_comment_public = RateLimit(LIMIT_COMMENT_PUBLIC_PER_MIN, 60, "comment_public")
rate_limit_upload_image = RateLimit(LIMIT_UPLOAD_IMAGE_PER_MIN, 60, "upload_image")


def require_rate_limit_login(request: Request) -> None:
    """供 Depends() 使用。勿直接 Depends(rate_limit_login)：类实例 __call__ 在部分 FastAPI 下会把 request 误判为 query 参数。"""
    rate_limit_login(request)


def require_rate_limit_auth_captcha(request: Request) -> None:
    rate_limit_auth_captcha(request)


def require_rate_limit_comment_public(request: Request) -> None:
    rate_limit_comment_public(request)


def require_rate_limit_upload_image(request: Request) -> None:
    rate_limit_upload_image(request)
