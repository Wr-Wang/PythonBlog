"""专栏后台管理接口。"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models import ColumnModel, ColumnPost, Post, User
from app.schemas import (
    ColumnAdminOut,
    ColumnCreate,
    ColumnPostBrief,
    ColumnPublicDetailOut,
    ColumnPublicListItem,
    ColumnUpdate,
)
from app.schemas.page import Page
from app.services.crud_utils import (
    apply_updates,
    commit_and_refresh,
    delete_and_commit,
    ensure_unique_field,
    get_by_id_or_404,
)

router = APIRouter(prefix="/api/columns", tags=["columns"])


def _column_load_links_posts_author():
    """专栏关联预加载：post_links -> post -> author。"""
    return (
        selectinload(ColumnModel.post_links)
        .selectinload(ColumnPost.post)
        .selectinload(Post.author)
    )


def _sorted_links(row: ColumnModel) -> list[ColumnPost]:
    """按 sort_order 排序，post_id 作为稳定次序兜底。"""
    return sorted(row.post_links, key=lambda x: (x.sort_order, x.post_id))


def _admin_to_out(row: ColumnModel) -> ColumnAdminOut:
    """专栏模型转后台输出结构（含有序 post_ids/post_titles）。"""
    links = _sorted_links(row)
    post_ids = [x.post_id for x in links]
    post_titles = [(x.post.title if x.post is not None else "") for x in links]
    return ColumnAdminOut(
        id=row.id,
        name=row.name,
        slug=row.slug,
        description=row.description,
        cover_image_url=row.cover_image_url,
        is_public=row.is_public,
        author_id=row.author_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        post_ids=post_ids,
        post_titles=post_titles,
    )


def _public_detail_to_out(row: ColumnModel) -> ColumnPublicDetailOut:
    """专栏模型转前台详情结构（仅输出已发布文章）。"""
    items: list[ColumnPostBrief] = []
    for x in _sorted_links(row):
        p = x.post
        if p is None or not p.published:
            continue
        items.append(
            ColumnPostBrief(
                id=p.id,
                title=p.title,
                slug=p.slug,
                published_at=p.published_at,
                author_name=p.author_name,
            )
        )
    return ColumnPublicDetailOut(
        id=row.id,
        name=row.name,
        slug=row.slug,
        description=row.description,
        cover_image_url=row.cover_image_url,
        is_public=row.is_public,
        author_id=row.author_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        posts=items,
    )


def _public_list_item(row: ColumnModel) -> ColumnPublicListItem:
    """专栏模型转前台列表卡片（带可见文章数）。"""
    n = 0
    for x in _sorted_links(row):
        if x.post is not None and x.post.published:
            n += 1
    return ColumnPublicListItem(
        id=row.id,
        name=row.name,
        slug=row.slug,
        description=row.description,
        cover_image_url=row.cover_image_url,
        updated_at=row.updated_at,
        visible_post_count=n,
    )


def _set_column_posts(db: Session, column_id: int, post_ids: list[int]) -> None:
    """按数组顺序写入关联；先清空再插入。"""
    seen: set[int] = set()
    ordered: list[int] = []
    for pid in post_ids:
        if pid in seen:
            continue
        seen.add(pid)
        ordered.append(int(pid))
    db.query(ColumnPost).filter(ColumnPost.column_id == column_id).delete(synchronize_session=False)
    if not ordered:
        return
    rows = db.query(Post).filter(Post.id.in_(ordered)).all()
    by_id = {p.id: p for p in rows}
    missing = [pid for pid in ordered if pid not in by_id]
    if missing:
        raise HTTPException(status_code=400, detail=f"文章不存在: {missing}")
    for i, pid in enumerate(ordered):
        db.add(ColumnPost(column_id=column_id, post_id=pid, sort_order=i))


@router.get("", response_model=Page[ColumnPublicListItem])
def list_public_columns(
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """前台专栏列表（仅 is_public=True）。"""
    base = db.query(ColumnModel).filter(ColumnModel.is_public == True)  # noqa: E712
    total = base.count()
    rows = (
        base.options(_column_load_links_posts_author())
        .order_by(ColumnModel.updated_at.desc(), ColumnModel.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return Page(items=[_public_list_item(r) for r in rows], total=total)


@router.get("/by-slug/{slug}", response_model=ColumnPublicDetailOut)
def get_public_column_by_slug(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
):
    """前台专栏详情（slug 查询，仅公开专栏）。"""
    row = (
        db.query(ColumnModel)
        .options(_column_load_links_posts_author())
        .filter(ColumnModel.slug == slug, ColumnModel.is_public == True)  # noqa: E712
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="专栏不存在")
    return _public_detail_to_out(row)


@router.get("/admin", response_model=Page[ColumnAdminOut])
def list_columns(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    """后台专栏分页列表。"""
    total = db.query(ColumnModel).count()
    rows = (
        db.query(ColumnModel)
        .options(_column_load_links_posts_author())
        .order_by(ColumnModel.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return Page(items=[_admin_to_out(r) for r in rows], total=total)


@router.post("/admin", response_model=ColumnAdminOut, status_code=status.HTTP_201_CREATED)
def create_column(
    body: ColumnCreate,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
):
    """创建专栏并按 post_ids 写入有序绑定关系。"""
    ensure_unique_field(db, ColumnModel, "slug", body.slug, "slug 已存在")
    row = ColumnModel(
        name=body.name,
        slug=body.slug,
        description=body.description,
        cover_image_url=body.cover_image_url,
        is_public=body.is_public,
        author_id=current.id,
    )
    db.add(row)
    db.flush()
    if body.post_ids:
        _set_column_posts(db, row.id, body.post_ids)
    commit_and_refresh(db, row)
    row = (
        db.query(ColumnModel)
        .options(_column_load_links_posts_author())
        .filter(ColumnModel.id == row.id)
        .first()
    )
    return _admin_to_out(row)


@router.patch("/admin/{column_id}", response_model=ColumnAdminOut)
def update_column(
    column_id: int,
    body: ColumnUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    """更新专栏；可同时更新绑定文章顺序。"""
    row = (
        db.query(ColumnModel)
        .options(selectinload(ColumnModel.post_links))
        .filter(ColumnModel.id == column_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="专栏不存在")
    data = body.model_dump(exclude_unset=True)
    post_ids = data.pop("post_ids", None)
    if "slug" in data and data["slug"] != row.slug:
        ensure_unique_field(db, ColumnModel, "slug", data["slug"], "slug 已存在", exclude_id=column_id)
    apply_updates(row, data)
    if post_ids is not None:
        _set_column_posts(db, row.id, post_ids)
    commit_and_refresh(db, row)
    row = (
        db.query(ColumnModel)
        .options(_column_load_links_posts_author())
        .filter(ColumnModel.id == row.id)
        .first()
    )
    return _admin_to_out(row)


@router.delete("/admin/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_column(
    column_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    """删除专栏（关联 column_posts 由级联处理）。"""
    row = get_by_id_or_404(db, ColumnModel, column_id, "专栏不存在")
    delete_and_commit(db, row)
    return None
