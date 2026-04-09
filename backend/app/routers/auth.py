"""
认证 HTTP 路由：登录、当前用户、登出占位。

- /login：校验用户名密码后发 JWT。
- /me：依赖 get_current_user 解析 Bearer。
- /logout：仅文档友好；实际登出由前端清除 token。
"""
from fastapi import APIRouter, Depends, HTTPException, status  # 第三方：路由与异常
from pydantic import BaseModel  # 第三方：请求体模型
from sqlalchemy.orm import Session  # 第三方：会话类型

from app.auth_utils import create_access_token, verify_password  # 项目内：令牌与密码校验
from app.database import get_db  # 项目内：会话依赖
from app.deps import get_current_user  # 项目内：JWT 用户依赖
from app.models import User  # 项目内：ORM
from app.schemas import Token, UserOut  # 项目内：响应模型

router = APIRouter(prefix="/api/auth", tags=["auth"])  # 本模块所有路径以 /api/auth 开头


class LoginBody(BaseModel):
    """POST /login 的 JSON 体。"""

    username: str
    password: str


@router.post("/login", response_model=Token)  # 201 默认 POST 成功 200；登录成功返回 Token
def login(body: LoginBody, db: Session = Depends(get_db)):  # Body 自动解析 JSON
    user = db.query(User).filter(User.username == body.username).first()  # 按用户名查
    if user is None or not verify_password(body.password, user.hashed_password):  # 防用户名枚举可统一文案
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已禁用")  # 403 已认证但无权限
    token = create_access_token(user.username)  # sub=用户名
    return Token(access_token=token)  # response_model 再包一层 token_type


@router.get("/me", response_model=UserOut)  # 需 Authorization: Bearer
def me(current: User = Depends(get_current_user)):  # 依赖注入当前用户
    return current  # ORM -> UserOut，from_attributes 生效


@router.post("/logout")
def logout():
    """前端应清除本地令牌；此处仅占位便于文档列出接口。"""
    return {"ok": True}
