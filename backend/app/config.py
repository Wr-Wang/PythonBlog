"""
应用配置（pydantic-settings）。

语法要点：
- BaseSettings：从环境变量、.env 文件自动填充字段名（DATABASE_URL 对应 database_url）。
- SettingsConfigDict：model_config 指定 env 文件路径与编码。
- @field_validator：在赋值/校验阶段对字段做自定义校验（Pydantic v2）。
"""
from pathlib import Path  # 标准库：路径

from pydantic import field_validator  # 第三方：字段校验装饰器
from pydantic_settings import BaseSettings, SettingsConfigDict  # 第三方：配置基类与配置字典

_BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend 目录（config.py 在 app/ 下）


class Settings(BaseSettings):
    """全局配置项；实例化时自动读 backend/.env 与环境变量。"""

    # model_config：Pydantic v2 中类配置入口（替代旧的 Config 内部类）
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),  # 相对工作目录易错，故写绝对路径
        env_file_encoding="utf-8",  # Windows 下 .env 常用 UTF-8
        extra="ignore",  # .env 里多出的键不报错
    )

    database_url: str  # 必填；无默认值则必须从 env/.env 提供
    admin_username: str = "admin"  # 有默认值时可被环境变量覆盖
    admin_password: str = "admin123"
    secret_key: str = "change-me-in-production-use-long-random-string"  # JWT 签名密钥
    algorithm: str = "HS256"  # jose 支持的算法名
    access_token_expire_minutes: int = 60 * 24  # 整数运算：一天分钟数
    cors_origins: str = (  # 多来源用逗号拼接，中间件里再 split
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173"
    )
    # 文章封面上传等静态文件目录（相对 backend 目录）
    upload_dir: str = str(_BACKEND_DIR / "uploads")

    @field_validator("database_url")  # 仅校验 database_url 字段
    @classmethod  # 类方法：第一个参数 cls 为 Settings 类
    def sql_server_only(cls, v: str) -> str:
        """强制使用 SQL Server 连接串前缀。"""
        u = (v or "").strip()  # or "" 防 None；strip 去首尾空白
        if not u.startswith("mssql+pyodbc://"):  # str 前缀判断
            raise ValueError("DATABASE_URL 须为 mssql+pyodbc://...，见 backend/.env.example")
        return u  # 校验通过原样返回


settings = Settings()  # 模块级单例：首次 import 时加载一次配置
