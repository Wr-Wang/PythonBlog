"""
分类 HTTP 路由：后台增删改查（路径均带 /admin 前缀，需 JWT）。

slug 全局唯一；删除前若有文章引用 category_id，可能受外键限制需先解绑。
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Category, User
from app.schemas import CategoryAdminOut, CategoryCreate, CategoryUpdate
from app.schemas.page import Page
from app.services.crud_utils import (
    apply_updates,
    commit_and_refresh,
    delete_and_commit,
    ensure_unique_field,
    get_by_id_or_404,
)

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("/admin", response_model=Page[CategoryAdminOut])
def list_categories(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    """后台分类分页列表。"""
    total = db.query(Category).count()
    rows = db.query(Category).order_by(Category.id.asc()).offset(skip).limit(limit).all()
    return Page(items=rows, total=total)


@router.get("/admin/{category_id}", response_model=CategoryAdminOut)
def get_category(
    category_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    """按 ID 获取单个分类。"""
    return get_by_id_or_404(db, Category, category_id, "分类不存在")


@router.post("/admin", response_model=CategoryAdminOut, status_code=status.HTTP_201_CREATED)
def create_category(
    body: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    """创建分类；slug 全局唯一。"""
    ensure_unique_field(db, Category, "slug", body.slug, "slug 已存在")
    c = Category(name=body.name, slug=body.slug)
    db.add(c)
    commit_and_refresh(db, c)
    return c


@router.patch("/admin/{category_id}", response_model=CategoryAdminOut)
def update_category(
    category_id: int,
    body: CategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    """更新分类；若修改 slug 需重新做唯一性校验。"""
    c = get_by_id_or_404(db, Category, category_id, "分类不存在")
    data = body.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] != c.slug:
        ensure_unique_field(db, Category, "slug", data["slug"], "slug 已存在", exclude_id=category_id)
    apply_updates(c, data)
    commit_and_refresh(db, c)
    return c


@router.delete("/admin/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    """删除分类（存在外键引用时由数据库约束兜底）。"""
    c = get_by_id_or_404(db, Category, category_id, "分类不存在")
    delete_and_commit(db, c)
    return None
