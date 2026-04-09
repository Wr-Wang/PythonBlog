"""
文章 HTTP 路由：公开列表/详情、后台 CRUD。

领域逻辑见 app.services.post_service。
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Post, User
from app.schemas import PostAdminOut, PostCreate, PostListItem, PostOut, PostUpdate
from app.services.post_service import ensure_category_exists, serialize_post_admin, set_post_tags

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("", response_model=list[PostListItem])
def list_posts(
    db: Annotated[Session, Depends(get_db)],
    published_only: bool = Query(True, description="公开列表仅显示已发布"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(Post).order_by(Post.created_at.desc())
    if published_only:
        q = q.filter(Post.published == True)  # noqa: E712
    return q.offset(skip).limit(limit).all()


@router.get("/admin", response_model=list[PostAdminOut])
def list_all_posts(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    rows = (
        db.query(Post).order_by(Post.created_at.desc()).offset(skip).limit(limit).all()
    )
    return [serialize_post_admin(p) for p in rows]


@router.get("/by-slug/{slug}", response_model=PostOut)
def get_by_slug(slug: str, db: Annotated[Session, Depends(get_db)]):
    post = db.query(Post).filter(Post.slug == slug).first()
    if post is None or not post.published:
        raise HTTPException(status_code=404, detail="文章不存在")
    return post


@router.get("/admin/{post_id}", response_model=PostAdminOut)
def admin_get_post(
    post_id: int,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    return serialize_post_admin(post)


@router.post("", response_model=PostAdminOut, status_code=status.HTTP_201_CREATED)
def create_post(
    body: PostCreate,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
):
    if db.query(Post).filter(Post.slug == body.slug).first():
        raise HTTPException(status_code=400, detail="slug 已存在")
    ensure_category_exists(db, body.category_id)
    post = Post(
        title=body.title,
        slug=body.slug,
        excerpt=body.excerpt,
        content=body.content,
        published=body.published,
        author_id=current.id,
        category_id=body.category_id,
        cover_image_url=body.cover_image_url,
    )
    db.add(post)
    db.flush()
    set_post_tags(db, post, body.tag_ids)
    db.commit()
    db.refresh(post)
    return serialize_post_admin(post)


@router.patch("/{post_id}", response_model=PostAdminOut)
def update_post(
    post_id: int,
    body: PostUpdate,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    data = body.model_dump(exclude_unset=True)
    tag_ids = data.pop("tag_ids", None)
    if "slug" in data and data["slug"] != post.slug:
        taken = db.query(Post).filter(Post.slug == data["slug"], Post.id != post_id).first()
        if taken:
            raise HTTPException(status_code=400, detail="slug 已存在")
    if "category_id" in data:
        ensure_category_exists(db, data["category_id"])
    for k, v in data.items():
        setattr(post, k, v)
    set_post_tags(db, post, tag_ids)
    db.commit()
    db.refresh(post)
    return serialize_post_admin(post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    db.delete(post)
    db.commit()
    return None
