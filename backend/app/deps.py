"""
FastAPI 依赖：从请求头解析 JWT 并加载当前用户。

语法要点：
- Annotated[T, Depends(x)]：类型注解 + 依赖注入，FastAPI 自动解析。
- HTTPBearer：从 Authorization: Bearer <token> 取凭证；auto_error=False 无头时不抛错而返回 None。
- HTTPException：统一错误响应；status 用 http.HTTPStatus 常量。
"""
from typing import Annotated  # 标准库：类型别名注解语法 PEP 695 之前常用此写法

from fastapi import Depends, HTTPException, status  # 第三方：依赖、异常、状态码枚举
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer  # 第三方：Bearer 方案
from jose import JWTError, jwt  # 第三方：JWT 编解码；JWTError 为校验失败异常
from sqlalchemy.orm import Session  # 第三方：ORM 会话类型

from app.config import settings  # 项目内：密钥与算法
from app.database import get_db  # 项目内：会话依赖
from app.models import User  # 项目内：用户模型
from app.models.rbac import Permission, Role, RolePermission, UserRole

security = HTTPBearer(auto_error=False)  # 无 Authorization 时 credentials 为 None 而非 403


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],  # 注入 Bearer
    db: Annotated[Session, Depends(get_db)],  # 注入数据库会话
) -> User:
    """
    保护路由：必须带合法 JWT；返回 ORM User。
    依赖链：security -> 解析头；get_db -> 会话。
    """
    if credentials is None:  # 未携带或格式不对（由 security 决定）
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,  # 401 未认证
            detail="未登录或令牌无效",
            headers={"WWW-Authenticate": "Bearer"},  # 提示客户端使用 Bearer
        )
    try:
        payload = jwt.decode(  # 验签 + 解析载荷；过期会抛 JWTError
            credentials.credentials, settings.secret_key, algorithms=[settings.algorithm]
        )
        username: str | None = payload.get("sub")  # dict.get 可能为 None
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    except JWTError:  # 过期、签名错误等
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    user = db.query(User).filter(User.username == username).first()  # 按用户名查一行
    if user is None or not user.is_active:  # 用户被删或禁用
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user


def get_user_permission_codes(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .filter(UserRole.user_id == user_id)
        .all()
    )
    return sorted({r[0] for r in rows if r and r[0]})


def user_has_permission(codes: list[str], permission_code: str) -> bool:
    if "admin.super" in codes or permission_code in codes:
        return True
    # 旧权限码兼容：避免升级后历史角色瞬间失效
    legacy_aliases: dict[str, tuple[str, ...]] = {
        "admin.roles.view": ("rbac.view",),
        "admin.permissions.view": ("rbac.view",),
        "admin.menus.view": ("rbac.view",),
        "admin.roles.create": ("rbac.manage",),
        "admin.roles.update": ("rbac.manage",),
        "admin.roles.bind_permissions": ("rbac.manage",),
        "admin.roles.bind_menus": ("rbac.manage",),
        "admin.menus.create": ("rbac.manage",),
        "admin.menus.update": ("rbac.manage",),
        "admin.users.bind_roles": ("rbac.manage",),
        "admin.audit.view": ("audit.view",),
        "admin.posts.publish.now": ("post.workflow",),
        "admin.posts.offline.now": ("post.workflow",),
    }
    return any(old_code in codes for old_code in legacy_aliases.get(permission_code, ()))


def require_permission(permission_code: str):
    def _dep(
        current: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
    ) -> None:
        # 超管约定：拥有 admin.super 则放行
        codes = get_user_permission_codes(db, current.id)
        if user_has_permission(codes, permission_code):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"缺少权限: {permission_code}",
        )

    return _dep


def get_user_data_scope(db: Session, user_id: int) -> str:
    rows = (
        db.query(Role.data_scope)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id, Role.is_active == True)  # noqa: E712
        .all()
    )
    scopes = {str(r[0] or "all").lower() for r in rows if r}
    if "all" in scopes:
        return "all"
    if "self" in scopes:
        return "self"
    return "all"
