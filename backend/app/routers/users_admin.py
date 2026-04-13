"""
用户 HTTP 路由：后台增删改查（含密码哈希）。

禁止删除当前登录账号，避免锁死后台；密码仅在创建或 PATCH 显式传入时更新。
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth_utils import hash_password
from app.database import get_db
from app.deps import get_current_user, require_permission
from app.models import User
from app.schemas import UserAdminCreate, UserAdminOut, UserAdminUpdate
from app.schemas.page import Page
from app.services.crud_utils import commit_and_refresh, delete_and_commit, ensure_unique_field, get_by_id_or_404

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/admin", response_model=Page[UserAdminOut])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    __: Annotated[None, Depends(require_permission("admin.users.view"))],
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    total = db.query(User).count()
    rows = db.query(User).order_by(User.id.asc()).offset(skip).limit(limit).all()
    return Page(items=rows, total=total)


@router.get("/admin/{user_id}", response_model=UserAdminOut)
def get_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    __: Annotated[None, Depends(require_permission("admin.users.view"))],
):
    return get_by_id_or_404(db, User, user_id, "用户不存在")


@router.post("/admin", response_model=UserAdminOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserAdminCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    __: Annotated[None, Depends(require_permission("admin.users.create"))],
):
    ensure_unique_field(db, User, "username", body.username, "用户名已存在")
    u = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        is_active=body.is_active,
    )
    db.add(u)
    commit_and_refresh(db, u)
    return u


@router.patch("/admin/{user_id}", response_model=UserAdminOut)
def update_user(
    user_id: int,
    body: UserAdminUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    __: Annotated[None, Depends(require_permission("admin.users.update"))],
):
    u = get_by_id_or_404(db, User, user_id, "用户不存在")
    data = body.model_dump(exclude_unset=True)
    if "username" in data and data["username"] != u.username:
        ensure_unique_field(db, User, "username", data["username"], "用户名已存在", exclude_id=user_id)
        u.username = data["username"]
    if "password" in data:
        u.hashed_password = hash_password(data["password"])
    if "is_active" in data:
        u.is_active = data["is_active"]
    commit_and_refresh(db, u)
    return u


@router.delete("/admin/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("admin.users.delete"))],
):
    if user_id == current.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录用户")
    u = get_by_id_or_404(db, User, user_id, "用户不存在")
    delete_and_commit(db, u)
    return None
