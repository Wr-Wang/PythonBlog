"""文章互动、举报与阅读指标接口。"""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Post
from app.models.interaction import PostFavorite, PostLike, PostReport, PostShare, PostViewEvent
from app.schemas.interaction import (
    InteractionStatsOut,
    PostActionBody,
    PostReportBody,
    PostShareBody,
    PostViewBody,
    PostViewMetricsOut,
)

router = APIRouter(prefix="/api/posts", tags=["post-interactions"])


def _must_post(db: Session, post_id: int) -> Post:
    p = db.query(Post).filter(Post.id == post_id).first()
    if p is None or not p.published:
        raise HTTPException(status_code=404, detail="文章不存在")
    return p


def _recalc_hot(post: Post) -> None:
    post.hot_score = int(
        (post.view_count or 0) * 1
        + (post.like_count or 0) * 5
        + (post.favorite_count or 0) * 8
        + (post.share_count or 0) * 6
    )


@router.post("/{post_id}/favorite")
def favorite_post(
    post_id: int,
    body: PostActionBody,
    db: Annotated[Session, Depends(get_db)],
):
    post = _must_post(db, post_id)
    row = (
        db.query(PostFavorite)
        .filter(PostFavorite.post_id == post_id, PostFavorite.user_key == body.user_key)
        .first()
    )
    if row is None:
        db.add(PostFavorite(post_id=post_id, user_key=body.user_key))
        post.favorite_count = (post.favorite_count or 0) + 1
        _recalc_hot(post)
        db.commit()
    return {"ok": True, "favorite_count": post.favorite_count}


@router.delete("/{post_id}/favorite")
def unfavorite_post(
    post_id: int,
    user_key: str | None = Query(None, min_length=1, max_length=128),
    body: PostActionBody | None = Body(default=None),
    db: Annotated[Session, Depends(get_db)] = None,
):
    post = _must_post(db, post_id)
    key = (user_key or (body.user_key if body else "")).strip()
    if not key:
        raise HTTPException(status_code=422, detail="缺少 user_key")
    row = (
        db.query(PostFavorite)
        .filter(PostFavorite.post_id == post_id, PostFavorite.user_key == key)
        .first()
    )
    if row is not None:
        db.delete(row)
        post.favorite_count = max(0, (post.favorite_count or 0) - 1)
        _recalc_hot(post)
        db.commit()
    return {"ok": True, "favorite_count": post.favorite_count}


@router.post("/{post_id}/unfavorite")
def unfavorite_post_via_post(
    post_id: int,
    body: PostActionBody,
    db: Annotated[Session, Depends(get_db)],
):
    post = _must_post(db, post_id)
    row = (
        db.query(PostFavorite)
        .filter(PostFavorite.post_id == post_id, PostFavorite.user_key == body.user_key)
        .first()
    )
    if row is not None:
        db.delete(row)
        post.favorite_count = max(0, (post.favorite_count or 0) - 1)
        _recalc_hot(post)
        db.commit()
    return {"ok": True, "favorite_count": post.favorite_count}


@router.post("/{post_id}/like")
def like_post(
    post_id: int,
    body: PostActionBody,
    db: Annotated[Session, Depends(get_db)],
):
    post = _must_post(db, post_id)
    row = db.query(PostLike).filter(PostLike.post_id == post_id, PostLike.user_key == body.user_key).first()
    if row is None:
        db.add(PostLike(post_id=post_id, user_key=body.user_key))
        post.like_count = (post.like_count or 0) + 1
        _recalc_hot(post)
        db.commit()
    return {"ok": True, "like_count": post.like_count}


@router.delete("/{post_id}/like")
def unlike_post(
    post_id: int,
    user_key: str | None = Query(None, min_length=1, max_length=128),
    body: PostActionBody | None = Body(default=None),
    db: Annotated[Session, Depends(get_db)] = None,
):
    post = _must_post(db, post_id)
    key = (user_key or (body.user_key if body else "")).strip()
    if not key:
        raise HTTPException(status_code=422, detail="缺少 user_key")
    row = db.query(PostLike).filter(PostLike.post_id == post_id, PostLike.user_key == key).first()
    if row is not None:
        db.delete(row)
        post.like_count = max(0, (post.like_count or 0) - 1)
        _recalc_hot(post)
        db.commit()
    return {"ok": True, "like_count": post.like_count}


@router.post("/{post_id}/unlike")
def unlike_post_via_post(
    post_id: int,
    body: PostActionBody,
    db: Annotated[Session, Depends(get_db)],
):
    post = _must_post(db, post_id)
    row = db.query(PostLike).filter(PostLike.post_id == post_id, PostLike.user_key == body.user_key).first()
    if row is not None:
        db.delete(row)
        post.like_count = max(0, (post.like_count or 0) - 1)
        _recalc_hot(post)
        db.commit()
    return {"ok": True, "like_count": post.like_count}


@router.post("/{post_id}/share")
def share_post(
    post_id: int,
    body: PostShareBody,
    db: Annotated[Session, Depends(get_db)],
):
    post = _must_post(db, post_id)
    db.add(PostShare(post_id=post_id, channel=body.channel, user_key=body.user_key))
    post.share_count = (post.share_count or 0) + 1
    _recalc_hot(post)
    db.commit()
    return {"ok": True, "share_count": post.share_count}


@router.post("/{post_id}/report", status_code=status.HTTP_201_CREATED)
def report_post(
    post_id: int,
    body: PostReportBody,
    db: Annotated[Session, Depends(get_db)],
):
    _must_post(db, post_id)
    db.add(
        PostReport(
            post_id=post_id,
            reason=body.reason,
            detail=body.detail,
            user_key=body.user_key,
        )
    )
    db.commit()
    return {"ok": True}


@router.post("/{post_id}/view")
def track_view(
    post_id: int,
    body: PostViewBody,
    db: Annotated[Session, Depends(get_db)],
):
    post = _must_post(db, post_id)
    db.add(
        PostViewEvent(
            post_id=post_id,
            user_key=body.user_key,
            duration_sec=body.duration_sec,
            completed=body.completed,
        )
    )
    post.view_count = (post.view_count or 0) + 1
    _recalc_hot(post)
    db.commit()
    return {"ok": True, "view_count": post.view_count}


@router.get("/{post_id}/interaction-stats", response_model=InteractionStatsOut)
def get_interaction_stats(post_id: int, db: Annotated[Session, Depends(get_db)]):
    post = _must_post(db, post_id)
    report_count = db.query(func.count(PostReport.id)).filter(PostReport.post_id == post_id).scalar() or 0
    return InteractionStatsOut(
        favorite_count=post.favorite_count or 0,
        like_count=post.like_count or 0,
        view_count=post.view_count or 0,
        share_count=post.share_count or 0,
        report_count=int(report_count),
        hot_score=post.hot_score or 0,
    )


@router.get("/{post_id}/view-metrics", response_model=PostViewMetricsOut)
def get_view_metrics(post_id: int, db: Annotated[Session, Depends(get_db)]):
    _must_post(db, post_id)
    q = db.query(PostViewEvent).filter(PostViewEvent.post_id == post_id)
    total = q.count()
    if total == 0:
        return PostViewMetricsOut(
            today_views=0,
            avg_duration_sec=0,
            completion_rate=0.0,
            generated_at=datetime.now(),
        )
    avg_duration = q.with_entities(func.avg(PostViewEvent.duration_sec)).scalar() or 0
    completed = q.filter(PostViewEvent.completed == True).count()  # noqa: E712
    today = (
        db.query(func.count(PostViewEvent.id))
        .filter(
            PostViewEvent.post_id == post_id,
            func.convert(func.DATE, PostViewEvent.created_at) == func.convert(func.DATE, func.getdate()),
        )
        .scalar()
        or 0
    )
    return PostViewMetricsOut(
        today_views=int(today),
        avg_duration_sec=int(float(avg_duration)),
        completion_rate=round(float(completed) / float(total), 4),
        generated_at=datetime.now(),
    )
