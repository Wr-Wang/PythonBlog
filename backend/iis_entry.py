"""
IIS HttpPlatformHandler 专用入口。

IIS 会将对外端口映射为子进程端口，并设置环境变量 HTTP_PLATFORM_PORT。
部分环境下 web.config 中 --port %HTTP_PLATFORM_PORT% 无法被正确替换，导致 502.3；
此处从环境变量读取端口再启动 uvicorn，避免依赖 CMD 对 % 的展开。
"""
from __future__ import annotations

import os
import sys


def main() -> None:
    raw = os.environ.get("HTTP_PLATFORM_PORT")
    if not raw:
        sys.stderr.write(
            "iis_entry: 缺少环境变量 HTTP_PLATFORM_PORT。"
            "请确认已安装 HttpPlatformHandler 且站点由该模块启动子进程。\n"
        )
        sys.exit(1)
    port = int(raw)
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
