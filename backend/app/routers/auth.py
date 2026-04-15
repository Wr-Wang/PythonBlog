"""
认证 HTTP 路由：登录、当前用户、登出占位。

- /login：校验用户名密码后发 JWT；同一用户名密码错误 ≥1 次后须带轮换验证码。
- /captcha：获取验证码（图形 / 算术轮换）。
- /me：依赖 get_current_user 解析 Bearer。
- /logout：仅文档友好；实际登出由前端清除 token。
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth_utils import create_access_token, verify_password
from app.captcha_service import (
    clear_login_failures,
    issue_captcha,
    needs_captcha_after_failed_password,
    record_password_failure,
    verify_and_consume,
)
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.models.rbac import Menu, Permission, Role, RoleMenu, RolePermission, UserRole
from app.rate_limit import require_rate_limit_auth_captcha, require_rate_limit_login
from app.schemas import Token, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    """POST /login 的 JSON 体。"""

    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)
    captcha_id: str | None = None
    captcha_answer: str | None = None


@router.get("/captcha")
def get_captcha(_: Annotated[None, Depends(require_rate_limit_auth_captcha)]):
    """签发新验证码；每次请求在图形与算术形态间轮换。"""
    return issue_captcha()


@router.post("/login", response_model=Token)
def login(
    body: LoginBody,
    _: Annotated[None, Depends(require_rate_limit_login)],
    db: Session = Depends(get_db),
):
    u = body.username.strip()
    need = needs_captcha_after_failed_password(u)
    if need:
        ok, err_msg = verify_and_consume(body.captcha_id, body.captcha_answer)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": err_msg, "captcha_required": True},
            )

    user = db.query(User).filter(User.username == u).first()
    if user is None or not verify_password(body.password, user.hashed_password):
        record_password_failure(u)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "用户名或密码错误", "captcha_required": True},
        )

    if not user.is_active:
        clear_login_failures(u)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已禁用")

    clear_login_failures(u)
    token = create_access_token(user.username)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role_rows = (
        db.query(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == current.id, Role.is_active == True)  # noqa: E712
        .all()
    )
    roles = sorted({r[0] for r in role_rows if r and r[0]})
    perm_rows = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .filter(UserRole.user_id == current.id)
        .all()
    )
    permission_codes = sorted({r[0] for r in perm_rows if r and r[0]})
    menu_rows = (
        db.query(Menu.route)
        .join(RoleMenu, RoleMenu.menu_id == Menu.id)
        .join(UserRole, UserRole.role_id == RoleMenu.role_id)
        .filter(UserRole.user_id == current.id, Menu.hidden == False)  # noqa: E712
        .all()
    )
    menus = sorted({r[0] for r in menu_rows if r and r[0]})
    return UserOut(
        id=current.id,
        username=current.username,
        is_active=current.is_active,
        roles=roles,
        permissions=permission_codes,
        menus=menus,
    )


@router.post("/logout")
def logout():
    """前端应清除本地令牌；此处仅占位便于文档列出接口。"""
    return {"ok": True}
