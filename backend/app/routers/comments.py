"""
评论 HTTP 路由：后台 CRUD、按 post_id 的公开列表与发表评论（含 parent_id 回复）。

行组装逻辑见 app.services.comment_service。
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.rate_limit import require_rate_limit_comment_public
from app.deps import get_current_user
from app.models import Comment, Post, User
from app.schemas import (
    CommentAdminCreate,
    CommentAdminOut,
    CommentAdminUpdate,
    CommentCreatePublic,
    CommentPublicOut,
)
from app.schemas.page import Page
from app.services.comment_service import comment_to_admin_out

router = APIRouter(prefix="/api/comments", tags=["comments"])


@router.get("/admin", response_model=Page[CommentAdminOut])
def list_comments_admin(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    total = db.query(Comment).count()
    rows = (
        db.query(Comment, Post.title)
        .join(Post, Comment.post_id == Post.id)
        .order_by(Comment.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return Page(
        items=[comment_to_admin_out(c, title) for c, title in rows],
        total=total,
    )


@router.get("/admin/{comment_id}", response_model=CommentAdminOut)
def get_comment_admin(
    comment_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    row = (
        db.query(Comment, Post.title)
        .join(Post, Comment.post_id == Post.id)
        .filter(Comment.id == comment_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="评论不存在")
    c, title = row
    return comment_to_admin_out(c, title)


@router.post("/admin", response_model=CommentAdminOut, status_code=status.HTTP_201_CREATED)
def create_comment_admin(
    body: CommentAdminCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    post = db.query(Post).filter(Post.id == body.post_id).first()
    if post is None:
        raise HTTPException(status_code=400, detail="文章不存在")
    if body.parent_id is not None:
        parent = (
            db.query(Comment)
            .filter(Comment.id == body.parent_id, Comment.post_id == body.post_id)
            .first()
        )
        if parent is None:
            raise HTTPException(status_code=400, detail="父评论不存在或不属于该文章")
    c = Comment(
        post_id=body.post_id,
        parent_id=body.parent_id,
        author_name=body.author_name,
        content=body.content,
        status=body.status,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return comment_to_admin_out(c, post.title)


@router.patch("/admin/{comment_id}", response_model=CommentAdminOut)
def update_comment_admin(
    comment_id: int,
    body: CommentAdminUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    c = db.query(Comment).filter(Comment.id == comment_id).first()
    if c is None:
        raise HTTPException(status_code=404, detail="评论不存在")
    upd = body.model_dump(exclude_unset=True, exclude={"content_b64"})
    # 仅传 content_b64 时，model_dump 可能不含 content；校验后由 body.content 写入
    if body.content_b64 is not None and str(body.content_b64).strip():
        upd["content"] = body.content
    for k, v in upd.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    post = db.query(Post).filter(Post.id == c.post_id).first()
    title = post.title if post else ""
    return comment_to_admin_out(c, title)


@router.delete("/admin/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment_admin(
    comment_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    c = db.query(Comment).filter(Comment.id == comment_id).first()
    if c is None:
        raise HTTPException(status_code=404, detail="评论不存在")
    db.delete(c)
    db.commit()
    return None


@router.get("/by-post/{post_id}", response_model=list[CommentPublicOut])
def list_comments_by_post_public(
    post_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None or not post.published:
        raise HTTPException(status_code=404, detail="文章不存在")
    return (
        db.query(Comment)
        .filter(
            Comment.post_id == post_id,
            or_(Comment.status == "approved", Comment.status.is_(None)),
        )
        .order_by(Comment.created_at.asc())
        .all()
    )


@router.post("/by-post/{post_id}", response_model=CommentPublicOut, status_code=status.HTTP_201_CREATED)
def create_comment_public(
    post_id: int,
    body: CommentCreatePublic,
    _: Annotated[None, Depends(require_rate_limit_comment_public)],
    db: Annotated[Session, Depends(get_db)],
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None or not post.published:
        raise HTTPException(status_code=404, detail="文章不存在")
    if body.parent_id is not None:
        parent = (
            db.query(Comment)
            .filter(Comment.id == body.parent_id, Comment.post_id == post_id)
            .first()
        )
        if parent is None:
            raise HTTPException(status_code=400, detail="父评论无效")
    c = Comment(
        post_id=post_id,
        parent_id=body.parent_id,
        author_name=body.author_name,
        content=body.content,
        status="pending",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c
