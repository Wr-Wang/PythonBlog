"""运营与效率：文章工作流、仪表盘统计。"""
from datetime import date, datetime, timedelta
import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Date, func
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from app.database import get_db
from app.datetime_utils import now_shanghai_naive
from app.deps import get_current_user, get_user_permission_codes, require_permission, user_has_permission
from app.models import Comment, Post, User
from app.models.interaction import PostFavorite, PostLike, PostReport, PostShare, PostViewEvent
from app.models.ops import BlacklistWord, FeatureFlag, SearchHotword, SearchSynonym, SensitiveWord

router = APIRouter(prefix="/api/admin/ops", tags=["ops"])

_POST_STATUS = {"draft", "pending", "approved", "rejected", "offline"}


def _parse_date_or_default(v: str | None, fallback: date) -> date:
    if not v:
        return fallback
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式无效: {v}") from e


def _daterange(start: date, end: date) -> list[date]:
    days = (end - start).days
    if days < 0:
        raise HTTPException(status_code=400, detail="start_date 不能大于 end_date")
    if days > 366:
        raise HTTPException(status_code=400, detail="时间范围不能超过 366 天")
    return [start + timedelta(days=i) for i in range(days + 1)]


def _rows_to_map(rows) -> dict[str, int]:
    out: dict[str, int] = {}
    for d, c in rows:
        out[str(d)] = int(c or 0)
    return out


@router.post("/posts/{post_id}/transition")
def transition_post(
    post_id: int,
    to_status: str = Query(..., min_length=3, max_length=20),
    db: Annotated[Session, Depends(get_db)] = None,
    _: Annotated[User, Depends(get_current_user)] = None,
):
    if to_status not in _POST_STATUS:
        raise HTTPException(status_code=400, detail="无效状态")
    codes = get_user_permission_codes(db, _.id)
    if to_status == "approved":
        if not (user_has_permission(codes, "admin.posts.publish.now") or user_has_permission(codes, "post.workflow")):
            raise HTTPException(status_code=403, detail="缺少权限: admin.posts.publish.now")
    elif to_status == "offline":
        if not (user_has_permission(codes, "admin.posts.offline.now") or user_has_permission(codes, "post.workflow")):
            raise HTTPException(status_code=403, detail="缺少权限: admin.posts.offline.now")
    elif not user_has_permission(codes, "post.workflow"):
        raise HTTPException(status_code=403, detail="缺少权限: post.workflow")
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    post.review_status = to_status
    if to_status == "approved":
        post.published = True
        if not post.published_at:
            post.published_at = now_shanghai_naive()
    if to_status == "offline":
        post.published = False
        post.offline_at = now_shanghai_naive()
    db.commit()
    return {"ok": True, "post_id": post.id, "review_status": post.review_status, "published": post.published}


@router.get("/dashboard", dependencies=[Depends(require_permission("admin.dashboard.view"))])
def dashboard_summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    posts_total = db.query(func.count(Post.id)).scalar() or 0
    published_total = db.query(func.count(Post.id)).filter(Post.published == True).scalar() or 0  # noqa: E712
    pending_total = db.query(func.count(Post.id)).filter(Post.review_status == "pending").scalar() or 0
    comments_total = db.query(func.count(Comment.id)).scalar() or 0
    comments_pending = db.query(func.count(Comment.id)).filter(Comment.status == "pending").scalar() or 0
    reports_pending = (
        db.query(func.count(PostReport.id)).filter(PostReport.reviewed == False).scalar() or 0  # noqa: E712
    )
    top_hot = (
        db.query(Post.id, Post.title, Post.hot_score)
        .order_by(Post.hot_score.desc(), Post.view_count.desc(), Post.id.desc())
        .limit(10)
        .all()
    )
    return {
        "posts_total": int(posts_total),
        "published_total": int(published_total),
        "pending_total": int(pending_total),
        "comments_total": int(comments_total),
        "comments_pending": int(comments_pending),
        "reports_pending": int(reports_pending),
        "top_hot_posts": [
            {"id": int(r[0]), "title": r[1], "hot_score": int(r[2] or 0)}
            for r in top_hot
        ],
    }


@router.get("/trends", dependencies=[Depends(require_permission("admin.dashboard.view"))])
def dashboard_trends(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
):
    today = now_shanghai_naive().date()
    start = _parse_date_or_default(start_date, today - timedelta(days=13))
    end = _parse_date_or_default(end_date, today)
    buckets = _daterange(start, end)

    views_map = _rows_to_map(
        db.query(func.cast(PostViewEvent.created_at, Date), func.count(PostViewEvent.id))
        .filter(
            PostViewEvent.created_at >= datetime.combine(start, datetime.min.time()),
            PostViewEvent.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time()),
        )
        .group_by(func.cast(PostViewEvent.created_at, Date))
        .all()
    )
    shares_map = _rows_to_map(
        db.query(func.cast(PostShare.created_at, Date), func.count(PostShare.id))
        .filter(
            PostShare.created_at >= datetime.combine(start, datetime.min.time()),
            PostShare.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time()),
        )
        .group_by(func.cast(PostShare.created_at, Date))
        .all()
    )
    likes_map = _rows_to_map(
        db.query(func.cast(PostLike.created_at, Date), func.count(PostLike.id))
        .filter(
            PostLike.created_at >= datetime.combine(start, datetime.min.time()),
            PostLike.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time()),
        )
        .group_by(func.cast(PostLike.created_at, Date))
        .all()
    )
    favorites_map = _rows_to_map(
        db.query(func.cast(PostFavorite.created_at, Date), func.count(PostFavorite.id))
        .filter(
            PostFavorite.created_at >= datetime.combine(start, datetime.min.time()),
            PostFavorite.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time()),
        )
        .group_by(func.cast(PostFavorite.created_at, Date))
        .all()
    )
    comments_map = _rows_to_map(
        db.query(func.cast(Comment.created_at, Date), func.count(Comment.id))
        .filter(
            Comment.created_at >= datetime.combine(start, datetime.min.time()),
            Comment.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time()),
        )
        .group_by(func.cast(Comment.created_at, Date))
        .all()
    )
    reports_map = _rows_to_map(
        db.query(func.cast(PostReport.created_at, Date), func.count(PostReport.id))
        .filter(
            PostReport.created_at >= datetime.combine(start, datetime.min.time()),
            PostReport.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time()),
        )
        .group_by(func.cast(PostReport.created_at, Date))
        .all()
    )
    publishes_map = _rows_to_map(
        db.query(func.cast(Post.published_at, Date), func.count(Post.id))
        .filter(
            Post.published_at.isnot(None),
            Post.published_at >= datetime.combine(start, datetime.min.time()),
            Post.published_at < datetime.combine(end + timedelta(days=1), datetime.min.time()),
        )
        .group_by(func.cast(Post.published_at, Date))
        .all()
    )

    points = []
    for d in buckets:
        k = str(d)
        points.append(
            {
                "date": k,
                "views": views_map.get(k, 0),
                "likes": likes_map.get(k, 0),
                "favorites": favorites_map.get(k, 0),
                "shares": shares_map.get(k, 0),
                "comments": comments_map.get(k, 0),
                "reports": reports_map.get(k, 0),
                "published_posts": publishes_map.get(k, 0),
            }
        )
    return {"start_date": str(start), "end_date": str(end), "points": points}


@router.get("/export")
def export_dashboard_trends(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
):
    if not user_has_permission(get_user_permission_codes(db, _.id), "admin.dashboard.export"):
        raise HTTPException(status_code=403, detail="缺少权限: admin.dashboard.export")
    data = dashboard_trends(db=db, _=_, start_date=start_date, end_date=end_date)
    points = data["points"]
    headers = ["date", "views", "likes", "favorites", "shares", "comments", "reports", "published_posts"]
    if format == "csv":
        sio = io.StringIO()
        writer = csv.DictWriter(sio, fieldnames=headers)
        writer.writeheader()
        writer.writerows(points)
        payload = sio.getvalue().encode("utf-8-sig")
        return StreamingResponse(
            io.BytesIO(payload),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="dashboard_trends.csv"'},
        )

    from openpyxl import Workbook  # 延迟导入，避免非导出场景额外开销

    wb = Workbook()
    ws = wb.active
    ws.title = "trends"
    ws.append(headers)
    for p in points:
        ws.append([p[h] for h in headers])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="dashboard_trends.xlsx"'},
    )


@router.get("/feature-flags", dependencies=[Depends(require_permission("admin.dashboard.view"))])
def list_feature_flags(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    rows = db.query(FeatureFlag).order_by(FeatureFlag.id.asc()).all()
    return [
        {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "enabled": r.enabled,
            "rollout_percent": int(r.rollout_percent or 0),
        }
        for r in rows
    ]


@router.post("/feature-flags/{flag_id}", dependencies=[Depends(require_permission("admin.flags.manage"))])
def update_feature_flag(
    flag_id: int,
    enabled: bool = Query(...),
    rollout_percent: int = Query(100, ge=0, le=100),
    db: Annotated[Session, Depends(get_db)] = None,
    _: Annotated[User, Depends(get_current_user)] = None,
):
    row = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="开关不存在")
    row.enabled = enabled
    row.rollout_percent = rollout_percent
    db.commit()
    return {"ok": True}


@router.get("/moderation", dependencies=[Depends(require_permission("admin.dashboard.view"))])
def moderation_lists(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    sensitive = [r.word for r in db.query(SensitiveWord).filter(SensitiveWord.enabled == True).all()]  # noqa: E712
    blacklist = [r.word for r in db.query(BlacklistWord).filter(BlacklistWord.enabled == True).all()]  # noqa: E712
    return {"sensitive_words": sensitive, "blacklist_words": blacklist}


@router.post("/moderation/sensitive", dependencies=[Depends(require_permission("admin.moderation.manage"))])
def add_sensitive_word(
    word: str = Query(..., min_length=1, max_length=64),
    db: Annotated[Session, Depends(get_db)] = None,
    _: Annotated[User, Depends(get_current_user)] = None,
):
    row = db.query(SensitiveWord).filter(SensitiveWord.word == word).first()
    if row is None:
        db.add(SensitiveWord(word=word, enabled=True))
    else:
        row.enabled = True
    db.commit()
    return {"ok": True}


@router.post("/moderation/blacklist", dependencies=[Depends(require_permission("admin.moderation.manage"))])
def add_blacklist_word(
    word: str = Query(..., min_length=1, max_length=64),
    db: Annotated[Session, Depends(get_db)] = None,
    _: Annotated[User, Depends(get_current_user)] = None,
):
    row = db.query(BlacklistWord).filter(BlacklistWord.word == word).first()
    if row is None:
        db.add(BlacklistWord(word=word, enabled=True))
    else:
        row.enabled = True
    db.commit()
    return {"ok": True}


@router.get("/search-ops", dependencies=[Depends(require_permission("admin.dashboard.view"))])
def search_ops(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    hot = (
        db.query(SearchHotword.keyword, SearchHotword.cnt)
        .order_by(SearchHotword.cnt.desc(), SearchHotword.id.asc())
        .limit(50)
        .all()
    )
    syn = db.query(SearchSynonym).filter(SearchSynonym.enabled == True).order_by(SearchSynonym.id.asc()).all()  # noqa: E712
    return {
        "hotwords": [{"keyword": x[0], "cnt": int(x[1] or 0)} for x in hot],
        "synonyms": [{"id": s.id, "src": s.src, "dst": s.dst} for s in syn],
    }


@router.post("/search-ops/synonyms", dependencies=[Depends(require_permission("admin.searchops.manage"))])
def add_synonym(
    src: str = Query(..., min_length=1, max_length=64),
    dst: str = Query(..., min_length=1, max_length=64),
    db: Annotated[Session, Depends(get_db)] = None,
    _: Annotated[User, Depends(get_current_user)] = None,
):
    row = db.query(SearchSynonym).filter(SearchSynonym.src == src, SearchSynonym.dst == dst).first()
    if row is None:
        db.add(SearchSynonym(src=src, dst=dst, enabled=True))
    else:
        row.enabled = True
    db.commit()
    return {"ok": True}
