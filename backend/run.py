"""
开发启动入口：在 backend 目录执行 `python run.py`。

语法要点：
- if __name__ == "__main__"`：仅在被直接运行该文件时执行，被 import 时不执行。
- uvicorn.run：以字符串 "app.main:app" 传入应用路径，支持 reload 热重载。
"""
import uvicorn  # 第三方：ASGI 服务器

if __name__ == "__main__":  # 脚本入口判断
    uvicorn.run(
        "app.main:app",  # 模块路径: 应用变量名（FastAPI 实例）
        host="0.0.0.0",  # 监听所有网卡，本机与局域网可访问
        port=8000,  # 端口
        reload=True,  # 开发模式：改代码自动重启子进程
    )
