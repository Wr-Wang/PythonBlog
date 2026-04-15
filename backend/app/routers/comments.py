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
from app.deps import get_current_user, get_user_data_scope
from app.models import Comment, Post, User
from app.models.ops import BlacklistWord, SensitiveWord
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


def _calc_comment_level_and_parent_author(
    db: Session,
    comment: Comment,
    cache: dict[int, tuple[int | None, str]],
) -> tuple[int, str | None]:
    level = 0
    pid = comment.parent_id
    parent_author = None
    # 最多追溯 10 层，防止异常数据导致死循环
    for _ in range(10):
        if pid is None:
            break
        level += 1
        node = cache.get(int(pid))
        if node is None:
            row = db.query(Comment.id, Comment.parent_id, Comment.author_name).filter(Comment.id == pid).first()
            if row is None:
                break
            cache[int(row[0])] = (row[1], row[2] or "")
            node = cache[int(pid)]
        if level == 1:
            parent_author = node[1] or None
        pid = node[0]
    return level, parent_author


def _prefetch_comment_chain_cache(
    db: Session,
    cache: dict[int, tuple[int | None, str]],
    max_depth: int = 10,
) -> None:
    """
    批量补齐父链缓存，避免逐条评论按 parent_id 回表（N+1）。
    仅预取当前页评论向上最多 max_depth 的祖先节点。
    """
    pending: set[int] = {
        int(parent_id)
        for parent_id, _ in cache.values()
        if parent_id is not None and int(parent_id) not in cache
    }
    for _ in range(max_depth):
        if not pending:
            break
        rows = (
            db.query(Comment.id, Comment.parent_id, Comment.author_name)
            .filter(Comment.id.in_(list(pending)))
            .all()
        )
        pending.clear()
        for cid, parent_id, author_name in rows:
            cache[int(cid)] = (parent_id, author_name or "")
        for parent_id, _ in cache.values():
            if parent_id is None:
                continue
            pid = int(parent_id)
            if pid not in cache:
                pending.add(pid)


@router.get("/admin", response_model=Page[CommentAdminOut])
def list_comments_admin(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    q = db.query(Comment, Post.title).join(Post, Comment.post_id == Post.id)
    if get_user_data_scope(db, current.id) == "self":
        q = q.filter(Post.author_id == current.id)
    total = q.count()
    rows = (
        q
        .order_by(Comment.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    chain_cache: dict[int, tuple[int | None, str]] = {}
    for c, _ in rows:
        chain_cache[int(c.id)] = (c.parent_id, c.author_name or "")
    _prefetch_comment_chain_cache(db, chain_cache)
    items: list[CommentAdminOut] = []
    for c, title in rows:
        level, parent_author = _calc_comment_level_and_parent_author(db, c, chain_cache)
        items.append(comment_to_admin_out(c, title, level=level, parent_author_name=parent_author))
    return Page(
        items=items,
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
    level, parent_author = _calc_comment_level_and_parent_author(db, c, {int(c.id): (c.parent_id, c.author_name or "")})
    return comment_to_admin_out(c, title, level=level, parent_author_name=parent_author)


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
    level, parent_author = _calc_comment_level_and_parent_author(db, c, {int(c.id): (c.parent_id, c.author_name or "")})
    return comment_to_admin_out(c, post.title, level=level, parent_author_name=parent_author)


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
    # 仅更新状态等字段时，不应把 content 覆盖为 None（否则触发数据库非空约束）
    if "content" in upd and upd.get("content") is None and body.content_b64 is None:
        upd.pop("content", None)
    # 仅传 content_b64 时，model_dump 可能不含 content；校验后由 body.content 写入
    if body.content_b64 is not None and str(body.content_b64).strip():
        upd["content"] = body.content
    next_status = upd.get("status")
    if next_status == "rejected":
        rtype = str(upd.get("reject_type") or "").strip()
        rreason = str(upd.get("reject_reason") or "").strip()
        if not rtype:
            raise HTTPException(status_code=400, detail="请填写拒绝类型")
        if not rreason:
            raise HTTPException(status_code=400, detail="请填写拒绝原因")
        upd["reject_type"] = rtype
        upd["reject_reason"] = rreason
    elif next_status == "approved":
        # 通过后清空拒绝信息
        upd["reject_type"] = None
        upd["reject_reason"] = None
    for k, v in upd.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    post = db.query(Post).filter(Post.id == c.post_id).first()
    title = post.title if post else ""
    level, parent_author = _calc_comment_level_and_parent_author(db, c, {int(c.id): (c.parent_id, c.author_name or "")})
    return comment_to_admin_out(c, title, level=level, parent_author_name=parent_author)


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
        .order_by(Comment.created_at.desc(), Comment.id.desc())
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
        # 默认直接通过；仅命中敏感词时转为待审核
        status="approved",
    )
    bl_words = [w.word for w in db.query(BlacklistWord).filter(BlacklistWord.enabled == True).all()]  # noqa: E712
    if any(w and w in body.content for w in bl_words):
        raise HTTPException(status_code=400, detail="评论包含黑名单词，已拦截")
    sen_words = [w.word for w in db.query(SensitiveWord).filter(SensitiveWord.enabled == True).all()]  # noqa: E712
    if any(w and w in body.content for w in sen_words):
        c.status = "pending"
    db.add(c)
    db.commit()
    db.refresh(c)
    return c
