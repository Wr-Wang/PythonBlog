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
from app.services.crud_utils import (
    apply_updates,
    commit_and_refresh,
    delete_and_commit,
    ensure_unique_field,
    get_by_id_or_404,
)

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("/admin", response_model=list[CategoryAdminOut])
def list_categories(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    return db.query(Category).order_by(Category.id.asc()).offset(skip).limit(limit).all()


@router.get("/admin/{category_id}", response_model=CategoryAdminOut)
def get_category(
    category_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return get_by_id_or_404(db, Category, category_id, "分类不存在")


@router.post("/admin", response_model=CategoryAdminOut, status_code=status.HTTP_201_CREATED)
def create_category(
    body: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
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
    c = get_by_id_or_404(db, Category, category_id, "分类不存在")
    delete_and_commit(db, c)
    return None
