"""
标签 HTTP 路由：后台增删改查。

与文章为多对多，删标签会清理 post_tags 关联行（数据库级 CASCADE）。
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Tag, User
from app.schemas import TagAdminOut, TagCreate, TagUpdate
from app.schemas.page import Page
from app.services.crud_utils import (
    apply_updates,
    commit_and_refresh,
    delete_and_commit,
    ensure_unique_field,
    get_by_id_or_404,
)

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("/admin", response_model=Page[TagAdminOut])
def list_tags(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    total = db.query(Tag).count()
    rows = db.query(Tag).order_by(Tag.id.asc()).offset(skip).limit(limit).all()
    return Page(items=rows, total=total)


@router.get("/admin/{tag_id}", response_model=TagAdminOut)
def get_tag(
    tag_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return get_by_id_or_404(db, Tag, tag_id, "标签不存在")


@router.post("/admin", response_model=TagAdminOut, status_code=status.HTTP_201_CREATED)
def create_tag(
    body: TagCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    ensure_unique_field(db, Tag, "slug", body.slug, "slug 已存在")
    t = Tag(name=body.name, slug=body.slug)
    db.add(t)
    commit_and_refresh(db, t)
    return t


@router.patch("/admin/{tag_id}", response_model=TagAdminOut)
def update_tag(
    tag_id: int,
    body: TagUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    t = get_by_id_or_404(db, Tag, tag_id, "标签不存在")
    data = body.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] != t.slug:
        ensure_unique_field(db, Tag, "slug", data["slug"], "slug 已存在", exclude_id=tag_id)
    apply_updates(t, data)
    commit_and_refresh(db, t)
    return t


@router.delete("/admin/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    t = get_by_id_or_404(db, Tag, tag_id, "标签不存在")
    delete_and_commit(db, t)
    return None
