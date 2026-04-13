"""
RBAC 与审计：
- 角色、权限点、菜单
- 用户-角色、角色-权限、角色-菜单
- 审计日志
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, NVARCHAR, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.datetime_utils import now_shanghai_naive


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(NVARCHAR(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(NVARCHAR(64), nullable=False)
    data_scope: Mapped[str] = mapped_column(NVARCHAR(20), nullable=False, default="all")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(NVARCHAR(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(NVARCHAR(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class Menu(Base):
    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(NVARCHAR(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(NVARCHAR(64), nullable=False)
    route: Mapped[str] = mapped_column(NVARCHAR(256), nullable=False)
    icon: Mapped[str | None] = mapped_column(NVARCHAR(64), nullable=True)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="UQ_user_roles_user_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="UQ_role_permissions"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class RoleMenu(Base):
    __tablename__ = "role_menus"
    __table_args__ = (UniqueConstraint("role_id", "menu_id", name="UQ_role_menus"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menus.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(NVARCHAR(128), nullable=False)
    target_type: Mapped[str] = mapped_column(NVARCHAR(64), nullable=False)
    target_id: Mapped[str] = mapped_column(NVARCHAR(64), nullable=False)
    detail: Mapped[str | None] = mapped_column(NVARCHAR(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)
