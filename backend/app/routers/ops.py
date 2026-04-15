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
from app.models import Category, Comment, Post, Tag, User
from app.models.interaction import PostFavorite, PostLike, PostReport, PostShare, PostViewEvent
from app.models.ops import BlacklistWord, FeatureFlag, SearchHotword, SearchSynonym, SensitiveWord

router = APIRouter(prefix="/api/admin/ops", tags=["ops"])

_POST_STATUS = {"draft", "pending", "approved", "rejected", "offline"}
_SENSITIVE_GROUPS: dict[str, dict] = {
    "abuse": {
        "name": "辱骂攻击",
        "words": ["辱骂词", "傻X", "傻逼", "脑残", "滚出去", "去死", "废物", "狗东西", "畜生", "贱人", "有病吧"],
    },
    "adult": {
        "name": "涉黄低俗",
        "words": ["色情", "成人交易", "约炮", "一夜情", "成人视频"],
    },
    "fraud": {
        "name": "诈骗赌博",
        "words": ["诈骗", "博彩", "赌博", "洗钱", "返利骗局", "高回报稳赚", "躺赚", "秒到账"],
    },
    "blackmarket": {
        "name": "灰黑产",
        "words": ["代开发票", "办证", "兼职刷单", "外挂", "木马", "钓鱼网站", "免实名", "跑分", "黑客接单", "社工库"],
    },
    "promotion": {
        "name": "引流推广",
        "words": ["网赚", "引流", "加V私聊", "VX联系", "QQ私聊", "Telegram群", "飞机群"],
    },
}


def _parse_date_or_default(v: str | None, fallback: date) -> date:
    """解析 YYYY-MM-DD；为空时使用默认值。"""
    if not v:
        return fallback
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式无效: {v}") from e


def _daterange(start: date, end: date) -> list[date]:
    """生成闭区间日期序列，并约束最大跨度。"""
    days = (end - start).days
    if days < 0:
        raise HTTPException(status_code=400, detail="start_date 不能大于 end_date")
    if days > 366:
        raise HTTPException(status_code=400, detail="时间范围不能超过 366 天")
    return [start + timedelta(days=i) for i in range(days + 1)]


def _rows_to_map(rows) -> dict[str, int]:
    """将 [(date, count)] 行集映射为 {'YYYY-MM-DD': count}。"""
    out: dict[str, int] = {}
    for d, c in rows:
        out[str(d)] = int(c or 0)
    return out


def _count_by_day(
    db: Session,
    dt_col,
    id_col,
    start: date,
    end: date,
    *extra_filters,
) -> dict[str, int]:
    """
    通用按天聚合计数器，统一 trends 内各指标查询形态，减少重复样板代码。
    """
    rows = (
        db.query(func.cast(dt_col, Date), func.count(id_col))
        .filter(
            dt_col >= datetime.combine(start, datetime.min.time()),
            dt_col < datetime.combine(end + timedelta(days=1), datetime.min.time()),
            *extra_filters,
        )
        .group_by(func.cast(dt_col, Date))
        .all()
    )
    return _rows_to_map(rows)


def _bucket_key(d: date, group_by: str) -> str:
    """根据粒度(day/week/month)生成聚合桶 key。"""
    if group_by == "week":
        y, w, _ = d.isocalendar()
        return f"{y}-W{w:02d}"
    if group_by == "month":
        return f"{d.year}-{d.month:02d}"
    return str(d)


def _group_points(points: list[dict], group_by: str) -> list[dict]:
    """将日级 points 聚合到周/月粒度。"""
    if group_by == "day":
        return points
    grouped: dict[str, dict] = {}
    order: list[str] = []
    sum_fields = [
        "views",
        "likes",
        "favorites",
        "shares",
        "comments",
        "reports",
        "published_posts",
        "created_posts",
    ]
    for row in points:
        d = datetime.strptime(row["date"], "%Y-%m-%d").date()
        key = _bucket_key(d, group_by)
        if key not in grouped:
            grouped[key] = {"date": key}
            for f in sum_fields:
                grouped[key][f] = 0
            order.append(key)
        for f in sum_fields:
            grouped[key][f] += int(row.get(f, 0) or 0)
    return [grouped[k] for k in order]


def _build_post_filters(
    start: date,
    end: date,
    category_id: int | None,
    author_id: int | None,
    review_status: str | None,
):
    """构建文章查询公共过滤条件集合。"""
    filters = [
        Post.created_at >= datetime.combine(start, datetime.min.time()),
        Post.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time()),
    ]
    if category_id:
        filters.append(Post.category_id == category_id)
    if author_id:
        filters.append(Post.author_id == author_id)
    if review_status:
        filters.append(Post.review_status == review_status)
    return filters


@router.post("/posts/{post_id}/transition")
def transition_post(
    post_id: int,
    to_status: str = Query(..., min_length=3, max_length=20),
    db: Annotated[Session, Depends(get_db)] = None,
    _: Annotated[User, Depends(get_current_user)] = None,
):
    """运营后台快捷流转文章状态（含权限校验）。"""
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
    # 流转目标文章必须存在。
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


@router.get("/dashboard")
def dashboard_summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    """看板概览：核心总量指标 + 热门文章 Top10。"""
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
    category_id: int | None = Query(None, ge=1),
    author_id: int | None = Query(None, ge=1),
    review_status: str | None = Query(None, min_length=3, max_length=20),
    group_by: str = Query("day", pattern="^(day|week|month)$"),
    chart_type: str = Query("line", pattern="^(line|bar|stack)$"),
    metrics: str | None = Query(None, description="逗号分隔：views,likes,comments..."),
):
    """多指标趋势数据：支持筛选、粒度聚合、指标裁剪。"""
    today = now_shanghai_naive().date()
    start = _parse_date_or_default(start_date, today - timedelta(days=13))
    end = _parse_date_or_default(end_date, today)
    buckets = _daterange(start, end)
    post_filters = _build_post_filters(start, end, category_id, author_id, review_status)

    views_map = _count_by_day(db, PostViewEvent.created_at, PostViewEvent.id, start, end)
    shares_map = _count_by_day(db, PostShare.created_at, PostShare.id, start, end)
    likes_map = _count_by_day(db, PostLike.created_at, PostLike.id, start, end)
    favorites_map = _count_by_day(db, PostFavorite.created_at, PostFavorite.id, start, end)
    comments_map = _count_by_day(db, Comment.created_at, Comment.id, start, end)
    reports_map = _count_by_day(db, PostReport.created_at, PostReport.id, start, end)
    publishes_map = _rows_to_map(
        db.query(func.cast(Post.published_at, Date), func.count(Post.id))
        .filter(
            Post.published_at.isnot(None),
            Post.published_at >= datetime.combine(start, datetime.min.time()),
            Post.published_at < datetime.combine(end + timedelta(days=1), datetime.min.time()),
            *(([Post.category_id == category_id] if category_id else [])),
            *(([Post.author_id == author_id] if author_id else [])),
            *(([Post.review_status == review_status] if review_status else [])),
        )
        .group_by(func.cast(Post.published_at, Date))
        .all()
    )
    created_posts_map = _rows_to_map(
        db.query(func.cast(Post.created_at, Date), func.count(Post.id))
        .filter(*post_filters)
        .group_by(func.cast(Post.created_at, Date))
        .all()
    )

    # 先构造日级点位，再根据 group_by 二次聚合。
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
                "created_posts": created_posts_map.get(k, 0),
            }
        )
    points = _group_points(points, group_by)
    all_metrics = [
        "views",
        "likes",
        "favorites",
        "shares",
        "comments",
        "reports",
        "published_posts",
        "created_posts",
    ]
    # 仅保留白名单指标，避免前端传入未知字段。
    requested_metrics = [x.strip() for x in (metrics or "").split(",") if x.strip()]
    selected_metrics = [x for x in requested_metrics if x in all_metrics] if requested_metrics else all_metrics
    series = [{"key": m, "name": m, "values": [int(p.get(m, 0) or 0) for p in points]} for m in selected_metrics]
    return {
        "start_date": str(start),
        "end_date": str(end),
        "filters": {
            "category_id": category_id,
            "author_id": author_id,
            "review_status": review_status,
            "group_by": group_by,
            "chart_type": chart_type,
        },
        "meta": {
            "group_by": group_by,
            "chart_type": chart_type,
            "metrics": selected_metrics,
        },
        "series": series,
        "points": points,
    }


@router.get("/dashboard/visual", dependencies=[Depends(require_permission("admin.dashboard.view"))])
def dashboard_visual(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
    category_id: int | None = Query(None, ge=1),
    author_id: int | None = Query(None, ge=1),
    review_status: str | None = Query(None, min_length=3, max_length=20),
):
    """可视化看板数据：KPI、漏斗、分布、榜单与筛选选项。"""
    today = now_shanghai_naive().date()
    start = _parse_date_or_default(start_date, today - timedelta(days=29))
    end = _parse_date_or_default(end_date, today)
    _daterange(start, end)
    post_filters = _build_post_filters(start, end, category_id, author_id, review_status)

    posts_total = db.query(func.count(Post.id)).filter(*post_filters).scalar() or 0
    published_total = db.query(func.count(Post.id)).filter(*post_filters, Post.published == True).scalar() or 0  # noqa: E712
    pending_total = db.query(func.count(Post.id)).filter(*post_filters, Post.review_status == "pending").scalar() or 0
    comments_total = db.query(func.count(Comment.id)).scalar() or 0
    comments_pending = db.query(func.count(Comment.id)).filter(Comment.status == "pending").scalar() or 0
    reports_pending = db.query(func.count(PostReport.id)).filter(PostReport.reviewed == False).scalar() or 0  # noqa: E712

    # 审核状态漏斗。
    workflow_counts = (
        db.query(Post.review_status, func.count(Post.id))
        .filter(*post_filters)
        .group_by(Post.review_status)
        .all()
    )
    workflow_map = {str(s or "unknown"): int(c or 0) for s, c in workflow_counts}

    # 分类分布 TopN。
    category_rows = (
        db.query(Category.name, func.count(Post.id))
        .select_from(Post)
        .outerjoin(Category, Category.id == Post.category_id)
        .filter(*post_filters)
        .group_by(Category.name)
        .order_by(func.count(Post.id).desc())
        .limit(8)
        .all()
    )

    # 标签分布 TopN。
    tag_rows = (
        db.query(Tag.name, func.count(Post.id))
        .select_from(Post)
        .outerjoin(Post.tags)
        .filter(*post_filters)
        .group_by(Tag.name)
        .order_by(func.count(Post.id).desc())
        .limit(8)
        .all()
    )

    # 热榜 TopN（按 hot_score + view_count）。
    hot_rows = (
        db.query(Post.id, Post.title, Post.hot_score, Post.view_count)
        .filter(*post_filters)
        .order_by(Post.hot_score.desc(), Post.view_count.desc(), Post.id.desc())
        .limit(10)
        .all()
    )

    # 举报次数子查询，用于风险文章榜单。
    report_cnt = (
        db.query(PostReport.post_id, func.count(PostReport.id).label("report_cnt"))
        .group_by(PostReport.post_id)
        .subquery()
    )
    risk_rows = (
        db.query(Post.id, Post.title, func.coalesce(report_cnt.c.report_cnt, 0))
        .outerjoin(report_cnt, report_cnt.c.post_id == Post.id)
        .filter(*post_filters)
        .order_by(func.coalesce(report_cnt.c.report_cnt, 0).desc(), Post.id.desc())
        .limit(10)
        .all()
    )
    # 筛选器可选项：分类/作者。
    category_opts = (
        db.query(Post.category_id, Category.name)
        .select_from(Post)
        .outerjoin(Category, Category.id == Post.category_id)
        .filter(Post.category_id.isnot(None))
        .group_by(Post.category_id, Category.name)
        .order_by(func.count(Post.id).desc())
        .limit(50)
        .all()
    )
    author_opts = (
        db.query(Post.author_id, User.username)
        .select_from(Post)
        .outerjoin(User, User.id == Post.author_id)
        .filter(Post.author_id.isnot(None))
        .group_by(Post.author_id, User.username)
        .order_by(func.count(Post.id).desc())
        .limit(50)
        .all()
    )

    return {
        "kpi": {
            "posts_total": int(posts_total),
            "published_total": int(published_total),
            "pending_total": int(pending_total),
            "comments_total": int(comments_total),
            "comments_pending": int(comments_pending),
            "reports_pending": int(reports_pending),
            "publish_rate": round((int(published_total) / int(posts_total) * 100), 2) if int(posts_total) else 0.0,
        },
        "workflow_funnel": [
            {"key": "draft", "label": "草稿", "count": int(workflow_map.get("draft", 0))},
            {"key": "pending", "label": "待审", "count": int(workflow_map.get("pending", 0))},
            {"key": "approved", "label": "已发布", "count": int(workflow_map.get("approved", 0))},
            {"key": "offline", "label": "已下线", "count": int(workflow_map.get("offline", 0))},
        ],
        "category_distribution": [{"name": (str(n).strip() if n and str(n).strip() else "未分类"), "count": int(c or 0)} for n, c in category_rows],
        "tag_distribution": [{"name": (str(n).strip() if n and str(n).strip() else "未打标"), "count": int(c or 0)} for n, c in tag_rows],
        "top_hot_posts": [
            {"id": int(i), "title": str(t), "hot_score": int(s or 0), "views": int(v or 0)}
            for i, t, s, v in hot_rows
        ],
        "top_risk_posts": [{"id": int(i), "title": str(t), "report_count": int(c or 0)} for i, t, c in risk_rows],
        "filter_options": {
            "categories": [{"id": int(i), "name": (str(n).strip() if n and str(n).strip() else "未分类")} for i, n in category_opts],
            "authors": [{"id": int(i), "name": (str(n).strip() if n and str(n).strip() else "未知作者")} for i, n in author_opts],
            "review_statuses": ["all", "draft", "pending", "approved", "rejected", "offline"],
        },
        "filters": {"start_date": str(start), "end_date": str(end), "category_id": category_id, "author_id": author_id, "review_status": review_status},
    }


@router.get("/export")
def export_dashboard_trends(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
    category_id: int | None = Query(None, ge=1),
    author_id: int | None = Query(None, ge=1),
    review_status: str | None = Query(None, min_length=3, max_length=20),
    group_by: str = Query("day", pattern="^(day|week|month)$"),
):
    """导出趋势数据（CSV/XLSX）。"""
    if not user_has_permission(get_user_permission_codes(db, _.id), "admin.dashboard.export"):
        raise HTTPException(status_code=403, detail="缺少权限: admin.dashboard.export")
    # 复用趋势接口逻辑，确保导出口径与页面一致。
    data = dashboard_trends(
        db=db,
        _=_,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        author_id=author_id,
        review_status=review_status,
        group_by=group_by,
    )
    points = data["points"]
    headers = ["date", "views", "likes", "favorites", "shares", "comments", "reports", "published_posts", "created_posts"]
    if format == "csv":
        # CSV 使用 utf-8-sig，兼容 Excel 直接打开中文。
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
    """查询功能开关列表。"""
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
    """更新单个功能开关状态与灰度比例。"""
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
    """查询审核词库（敏感词/黑名单）当前启用项。"""
    sensitive = [r.word for r in db.query(SensitiveWord).filter(SensitiveWord.enabled == True).all()]  # noqa: E712
    blacklist = [r.word for r in db.query(BlacklistWord).filter(BlacklistWord.enabled == True).all()]  # noqa: E712
    return {"sensitive_words": sensitive, "blacklist_words": blacklist}


@router.post("/moderation/sensitive", dependencies=[Depends(require_permission("admin.moderation.manage"))])
def add_sensitive_word(
    word: str = Query(..., min_length=1, max_length=64),
    db: Annotated[Session, Depends(get_db)] = None,
    _: Annotated[User, Depends(get_current_user)] = None,
):
    """新增或重新启用单个敏感词。"""
    row = db.query(SensitiveWord).filter(SensitiveWord.word == word).first()
    if row is None:
        db.add(SensitiveWord(word=word, enabled=True))
    else:
        row.enabled = True
    db.commit()
    return {"ok": True}


@router.get("/moderation/sensitive-groups", dependencies=[Depends(require_permission("admin.dashboard.view"))])
def list_sensitive_groups(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    """返回预置敏感词分组及启用覆盖情况。"""
    db_rows = db.query(SensitiveWord.word, SensitiveWord.enabled).all()
    enabled_map = {str(w): bool(e) for w, e in db_rows}
    out = []
    for code, meta in _SENSITIVE_GROUPS.items():
        words = list(meta["words"])
        enabled_count = sum(1 for w in words if enabled_map.get(w, False))
        out.append(
            {
                "code": code,
                "name": meta["name"],
                "total_words": len(words),
                "enabled_words": enabled_count,
                "all_enabled": enabled_count == len(words) and len(words) > 0,
                "words": words,
            }
        )
    return out


@router.post("/moderation/sensitive-groups/{group_code}", dependencies=[Depends(require_permission("admin.moderation.manage"))])
def toggle_sensitive_group(
    group_code: str,
    enabled: bool = Query(...),
    db: Annotated[Session, Depends(get_db)] = None,
    _: Annotated[User, Depends(get_current_user)] = None,
):
    """批量启用/禁用一个敏感词分组。"""
    meta = _SENSITIVE_GROUPS.get(group_code)
    if meta is None:
        raise HTTPException(status_code=404, detail="敏感词分组不存在")
    words = list(meta["words"])
    for w in words:
        row = db.query(SensitiveWord).filter(SensitiveWord.word == w).first()
        if row is None:
            db.add(SensitiveWord(word=w, enabled=enabled))
        else:
            row.enabled = enabled
    db.commit()
    return {"ok": True, "group_code": group_code, "enabled": enabled, "word_count": len(words)}


@router.post("/moderation/blacklist", dependencies=[Depends(require_permission("admin.moderation.manage"))])
def add_blacklist_word(
    word: str = Query(..., min_length=1, max_length=64),
    db: Annotated[Session, Depends(get_db)] = None,
    _: Annotated[User, Depends(get_current_user)] = None,
):
    """新增或重新启用单个黑名单词。"""
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
    """搜索运营数据：热词榜 + 同义词配置。"""
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
    """新增或重新启用同义词映射。"""
    row = db.query(SearchSynonym).filter(SearchSynonym.src == src, SearchSynonym.dst == dst).first()
    if row is None:
        db.add(SearchSynonym(src=src, dst=dst, enabled=True))
    else:
        row.enabled = True
    db.commit()
    return {"ok": True}
