"""
密码哈希与 JWT 签发。

语法要点：
- hashlib.sha256：对密码做摘要，再 bcrypt，规避 bcrypt 72 字节明文限制。
- bcrypt.hashpw / checkpw：字节入参；gensalt() 生成随机盐。
- jose.jwt.encode：HS256 对称签名；exp 用 Unix 秒时间戳。
- datetime.timezone.utc：JWT exp 惯例使用 UTC。
"""
import hashlib  # 标准库：SHA-256
from datetime import datetime, timedelta, timezone  # 标准库：时间运算与 UTC 时区

import bcrypt  # 第三方：bcrypt 哈希
from jose import jwt  # 第三方：JWT

from app.config import settings  # 项目内：密钥、算法、过期分钟数


def _sha256_hex(password: str) -> str:
    """密码转 UTF-8 字节后 SHA256，再 hex 成 64 字符 ASCII。"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """入库密码：bcrypt(sha256_hex(密码))，返回 str 供写入 VARCHAR。"""
    key = _sha256_hex(password).encode("ascii")  # 仅含 0-9a-f，定长
    return bcrypt.hashpw(key, bcrypt.gensalt()).decode("ascii")  # gensalt 内含轮数成本


def verify_password(plain: str, hashed: str) -> bool:
    """校验：先试新方案，再兼容旧版明文 bcrypt（≤72 字节）。"""
    try:
        hashed_b = hashed.encode("utf-8")  # bcrypt 需要 bytes
    except Exception:
        return False

    try:
        if bcrypt.checkpw(_sha256_hex(plain).encode("ascii"), hashed_b):  # 新方案
            return True
    except ValueError:  # 部分版本入参异常
        pass

    if not hashed.startswith("$2"):  # bcrypt 哈希均以 $2a/$2b 等开头
        return False
    raw = plain.encode("utf-8")
    if len(raw) > 72:  # 旧方案 bcrypt 明文上限
        return False
    try:
        return bcrypt.checkpw(raw, hashed_b)
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    """签发访问令牌；subject 一般为用户名，写入 JWT 的 sub。"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)  # UTC 时刻
    to_encode = {"sub": subject, "exp": int(expire.timestamp())}  # exp 须为数值时间戳
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)  # 返回 str JWT
