"""RBAC、菜单配置与审计查询接口。"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_user_permission_codes, require_permission, user_has_permission
from app.models import User
from app.models.rbac import (
    AuditLog,
    Menu,
    Permission,
    Role,
    RoleMenu,
    RolePermission,
    UserRole,
)
from app.schemas.page import Page
from app.schemas.rbac import (
    AuditLogOut,
    MenuCreate,
    MenuOut,
    MenuUpdate,
    PermissionBindBody,
    PermissionCreate,
    PermissionOut,
    RoleBindingsOut,
    RoleBindBody,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    UserRoleBindingsOut,
)
from app.services.audit_service import write_audit

router = APIRouter(prefix="/api/admin/rbac", tags=["rbac"])


@router.get("/roles", response_model=Page[RoleOut], dependencies=[Depends(require_permission("admin.roles.view"))])
def list_roles(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    q = db.query(Role).order_by(Role.id.asc())
    return Page(items=q.offset(skip).limit(limit).all(), total=q.count())


@router.post(
    "/roles",
    response_model=RoleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("admin.roles.create"))],
)
def create_role(
    body: RoleCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    if db.query(Role).filter(Role.code == body.code).first():
        raise HTTPException(status_code=400, detail="角色 code 已存在")
    row = Role(code=body.code, name=body.name, is_active=body.is_active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/roles/{role_id}", response_model=RoleOut, dependencies=[Depends(require_permission("admin.roles.update"))])
def update_role(
    role_id: int,
    body: RoleUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    row = db.query(Role).filter(Role.id == role_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.get(
    "/permissions",
    response_model=Page[PermissionOut],
)
def list_permissions(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    codes = get_user_permission_codes(db, _.id)
    if not (
        user_has_permission(codes, "admin.permissions.view")
        or user_has_permission(codes, "admin.roles.bind_permissions")
    ):
        raise HTTPException(status_code=403, detail="缺少权限: admin.permissions.view")
    q = db.query(Permission).order_by(Permission.id.asc())
    rows = q.all()
    return Page(items=rows, total=len(rows))


@router.post(
    "/permissions",
    response_model=PermissionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("admin.roles.bind_permissions"))],
)
def create_permission(
    body: PermissionCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    if db.query(Permission).filter(Permission.code == body.code).first():
        raise HTTPException(status_code=400, detail="权限 code 已存在")
    row = Permission(code=body.code, name=body.name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/menus", response_model=Page[MenuOut])
def list_menus(db: Annotated[Session, Depends(get_db)], _: Annotated[User, Depends(get_current_user)]):
    codes = get_user_permission_codes(db, _.id)
    if not (
        user_has_permission(codes, "admin.menus.view")
        or user_has_permission(codes, "admin.roles.bind_menus")
    ):
        raise HTTPException(status_code=403, detail="缺少权限: admin.menus.view")
    q = db.query(Menu).order_by(Menu.order_no.asc(), Menu.id.asc())
    rows = q.all()
    return Page(items=rows, total=len(rows))


@router.post(
    "/menus",
    response_model=MenuOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("admin.menus.create"))],
)
def create_menu(
    body: MenuCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    if db.query(Menu).filter(Menu.code == body.code).first():
        raise HTTPException(status_code=400, detail="菜单 code 已存在")
    row = Menu(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/menus/{menu_id}", response_model=MenuOut, dependencies=[Depends(require_permission("admin.menus.update"))])
def update_menu(
    menu_id: int,
    body: MenuUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    row = db.query(Menu).filter(Menu.id == menu_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="菜单不存在")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.post("/users/{user_id}/bind-roles", dependencies=[Depends(require_permission("admin.users.bind_roles"))])
def bind_user_roles(
    user_id: int,
    body: RoleBindBody,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    db.query(UserRole).filter(UserRole.user_id == user_id).delete()
    uniq = list(dict.fromkeys(body.role_ids))
    for rid in uniq:
        db.add(UserRole(user_id=user_id, role_id=rid))
    write_audit(
        db,
        actor=_,
        action="rbac.bind_user_roles",
        target_type="user",
        target_id=str(user_id),
        detail=",".join([str(x) for x in uniq]) or "[]",
    )
    db.commit()
    return {"ok": True, "role_ids": uniq}


@router.get(
    "/users/{user_id}/roles",
    response_model=UserRoleBindingsOut,
)
def get_user_roles(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    codes = get_user_permission_codes(db, _.id)
    if not (
        user_has_permission(codes, "admin.roles.view")
        or user_has_permission(codes, "admin.users.bind_roles")
    ):
        raise HTTPException(status_code=403, detail="缺少权限: admin.roles.view")
    rows = db.query(UserRole.role_id).filter(UserRole.user_id == user_id).all()
    return UserRoleBindingsOut(user_id=user_id, role_ids=[int(r[0]) for r in rows if r and r[0] is not None])


@router.post("/roles/{role_id}/bind")
def bind_role_permissions_and_menus(
    role_id: int,
    body: PermissionBindBody,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    codes = get_user_permission_codes(db, _.id)
    can_bind_perm = user_has_permission(codes, "admin.roles.bind_permissions")
    can_bind_menu = user_has_permission(codes, "admin.roles.bind_menus")
    existing_p_ids = [r[0] for r in db.query(RolePermission.permission_id).filter(RolePermission.role_id == role_id).all()]
    existing_m_ids = [r[0] for r in db.query(RoleMenu.menu_id).filter(RoleMenu.role_id == role_id).all()]
    p_ids = list(dict.fromkeys(body.permission_ids))
    m_ids = list(dict.fromkeys(body.menu_ids))
    if (not can_bind_perm) and (sorted(p_ids) != sorted(existing_p_ids)):
        raise HTTPException(status_code=403, detail="缺少权限: admin.roles.bind_permissions")
    if (not can_bind_menu) and (sorted(m_ids) != sorted(existing_m_ids)):
        raise HTTPException(status_code=403, detail="缺少权限: admin.roles.bind_menus")
    if not (can_bind_perm or can_bind_menu):
        raise HTTPException(status_code=403, detail="缺少角色绑定权限")
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
    db.query(RoleMenu).filter(RoleMenu.role_id == role_id).delete()
    for pid in p_ids:
        db.add(RolePermission(role_id=role_id, permission_id=pid))
    for mid in m_ids:
        db.add(RoleMenu(role_id=role_id, menu_id=mid))
    write_audit(
        db,
        actor=_,
        action="rbac.bind_role",
        target_type="role",
        target_id=str(role_id),
        detail=f"permissions={p_ids};menus={m_ids}",
    )
    db.commit()
    persisted_p_ids = [int(r[0]) for r in db.query(RolePermission.permission_id).filter(RolePermission.role_id == role_id).all()]
    persisted_m_ids = [int(r[0]) for r in db.query(RoleMenu.menu_id).filter(RoleMenu.role_id == role_id).all()]
    if sorted(set(persisted_p_ids)) != sorted(set(p_ids)):
        raise HTTPException(status_code=500, detail="权限点绑定写入失败：数据库未持久化")
    if sorted(set(persisted_m_ids)) != sorted(set(m_ids)):
        raise HTTPException(status_code=500, detail="菜单绑定写入失败：数据库未持久化")
    return {"ok": True, "permission_ids": persisted_p_ids, "menu_ids": persisted_m_ids}


@router.get(
    "/roles/{role_id}/bindings",
    response_model=RoleBindingsOut,
)
def get_role_bindings(
    role_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    codes = get_user_permission_codes(db, _.id)
    if not (
        user_has_permission(codes, "admin.roles.view")
        or user_has_permission(codes, "admin.roles.bind_permissions")
        or user_has_permission(codes, "admin.roles.bind_menus")
    ):
        raise HTTPException(status_code=403, detail="缺少权限: admin.roles.view")
    p_rows = db.query(RolePermission.permission_id).filter(RolePermission.role_id == role_id).all()
    m_rows = db.query(RoleMenu.menu_id).filter(RoleMenu.role_id == role_id).all()
    return RoleBindingsOut(
        role_id=role_id,
        permission_ids=[int(r[0]) for r in p_rows if r and r[0] is not None],
        menu_ids=[int(r[0]) for r in m_rows if r and r[0] is not None],
    )


@router.get("/audit-logs", response_model=Page[AuditLogOut], dependencies=[Depends(require_permission("admin.audit.view"))])
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    return Page(items=q.offset(skip).limit(limit).all(), total=q.count())
