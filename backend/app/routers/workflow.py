"""流程中心：统一待办池查询（Iteration 1 - first step）。"""
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.datetime_utils import now_shanghai_naive
from app.deps import get_current_user, get_user_permission_codes, user_has_permission
from app.models import Comment, Post, User
from app.models.interaction import PostReport
from app.models.workflow import WorkflowAudit, WorkflowReasonTemplate

router = APIRouter(prefix="/api/admin/workflow", tags=["workflow"])

_TASK_TYPES = {"all", "post", "comment", "report"}
_TASK_STATUSES = {"all", "pending", "approved", "rejected", "offline", "draft", "open", "closed"}
_BATCH_ACTIONS = {"approve", "reject", "offline", "reassign"}


def _can_view_workflow(db: Session, user_id: int) -> bool:
    codes = get_user_permission_codes(db, user_id)
    return (
        user_has_permission(codes, "admin.super")
        or user_has_permission(codes, "post.workflow")
        or user_has_permission(codes, "admin.posts.view")
        or user_has_permission(codes, "admin.dashboard.view")
    )


def _compute_priority(created_at: datetime) -> str:
    age_hours = max(0.0, (now_shanghai_naive() - created_at).total_seconds() / 3600)
    if age_hours >= 24:
        return "high"
    if age_hours >= 8:
        return "medium"
    return "low"


def _parse_date_range(start_date: str | None, end_date: str | None) -> tuple[datetime | None, datetime | None]:
    start_dt: datetime | None = None
    end_dt: datetime | None = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"invalid start_date: {start_date}") from e
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"invalid end_date: {end_date}") from e
    return start_dt, end_dt


class WorkflowBatchActionIn(BaseModel):
    task_ids: list[str] = Field(default_factory=list, min_length=1)
    action: str = Field(..., min_length=3, max_length=20)
    reason_template_id: int | None = None
    assignee_id: int | None = None
    remark: str | None = Field(default=None, max_length=500)


@router.get("/tasks")
def list_workflow_tasks(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    task_type: str = Query("all"),
    status: str = Query("all"),
    keyword: str | None = Query(None, min_length=1, max_length=80),
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    if task_type not in _TASK_TYPES:
        raise HTTPException(status_code=400, detail=f"invalid task_type: {task_type}")
    if status not in _TASK_STATUSES:
        raise HTTPException(status_code=400, detail=f"invalid status: {status}")
    if not _can_view_workflow(db, _.id):
        raise HTTPException(status_code=403, detail="forbidden")

    start_dt, end_dt = _parse_date_range(start_date, end_date)

    tasks: list[dict] = []
    kw = (keyword or "").strip()

    if task_type in {"all", "post"}:
        q = db.query(Post, User.username).outerjoin(User, User.id == Post.author_id)
        if status != "all":
            q = q.filter(Post.review_status == status)
        if kw:
            q = q.filter(Post.title.contains(kw))
        if start_dt:
            q = q.filter(Post.created_at >= start_dt)
        if end_dt:
            q = q.filter(Post.created_at < end_dt)
        rows = q.order_by(Post.created_at.desc()).limit(300).all()
        for p, author_name in rows:
            created = p.created_at or now_shanghai_naive()
            tasks.append(
                {
                    "id": f"post:{p.id}",
                    "task_type": "post",
                    "biz_id": p.id,
                    "title": p.title,
                    "status": p.review_status or ("approved" if p.published else "draft"),
                    "priority": _compute_priority(created),
                    "assignee_id": p.author_id,
                    "assignee_name": author_name or "未分配",
                    "sla_deadline": (created + timedelta(hours=24)).isoformat(timespec="seconds"),
                    "is_timeout": now_shanghai_naive() > created + timedelta(hours=24),
                    "created_at": created.isoformat(timespec="seconds"),
                }
            )

    if task_type in {"all", "comment"}:
        q = db.query(Comment, Post.title).outerjoin(Post, Post.id == Comment.post_id)
        if status != "all":
            q = q.filter(Comment.status == status)
        if kw:
            q = q.filter(Comment.content.contains(kw))
        if start_dt:
            q = q.filter(Comment.created_at >= start_dt)
        if end_dt:
            q = q.filter(Comment.created_at < end_dt)
        rows = q.order_by(Comment.created_at.desc()).limit(300).all()
        for c, post_title in rows:
            created = c.created_at or now_shanghai_naive()
            tasks.append(
                {
                    "id": f"comment:{c.id}",
                    "task_type": "comment",
                    "biz_id": c.id,
                    "title": f"评论@{post_title or ('文章' + str(c.post_id))}",
                    "status": c.status,
                    "priority": _compute_priority(created),
                    "assignee_id": None,
                    "assignee_name": c.author_name or "访客",
                    "sla_deadline": (created + timedelta(hours=24)).isoformat(timespec="seconds"),
                    "is_timeout": c.status == "pending" and now_shanghai_naive() > created + timedelta(hours=24),
                    "created_at": created.isoformat(timespec="seconds"),
                }
            )

    if task_type in {"all", "report"}:
        q = db.query(PostReport, Post.title).outerjoin(Post, Post.id == PostReport.post_id)
        if status == "open":
            q = q.filter(PostReport.reviewed == False)  # noqa: E712
        elif status == "closed":
            q = q.filter(PostReport.reviewed == True)  # noqa: E712
        elif status != "all":
            q = q.filter(PostReport.reviewed == (status in {"approved", "offline"}))
        if kw:
            q = q.filter(Post.title.contains(kw))
        if start_dt:
            q = q.filter(PostReport.created_at >= start_dt)
        if end_dt:
            q = q.filter(PostReport.created_at < end_dt)
        rows = q.order_by(PostReport.created_at.desc()).limit(300).all()
        for r, post_title in rows:
            created = r.created_at or now_shanghai_naive()
            tasks.append(
                {
                    "id": f"report:{r.id}",
                    "task_type": "report",
                    "biz_id": r.id,
                    "title": f"举报@{post_title or ('文章' + str(r.post_id))}",
                    "status": "closed" if r.reviewed else "open",
                    "priority": "high" if not r.reviewed else "low",
                    "assignee_id": None,
                    "assignee_name": "运营处理",
                    "sla_deadline": (created + timedelta(hours=24)).isoformat(timespec="seconds"),
                    "is_timeout": (not r.reviewed) and now_shanghai_naive() > created + timedelta(hours=24),
                    "created_at": created.isoformat(timespec="seconds"),
                }
            )

    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    total = len(tasks)
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    return {"total": total, "page": page, "size": size, "items": tasks[start_idx:end_idx]}


@router.get("/sla-summary")
def workflow_sla_summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    task_type: str = Query("all"),
    status: str = Query("all"),
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
):
    if task_type not in _TASK_TYPES:
        raise HTTPException(status_code=400, detail=f"invalid task_type: {task_type}")
    if status not in _TASK_STATUSES:
        raise HTTPException(status_code=400, detail=f"invalid status: {status}")
    if not _can_view_workflow(db, _.id):
        raise HTTPException(status_code=403, detail="forbidden")

    start_dt, end_dt = _parse_date_range(start_date, end_date)
    now = now_shanghai_naive()
    today_start = datetime(now.year, now.month, now.day)
    pending_count = 0
    timeout_count = 0

    if task_type in {"all", "post"} and status in {"all", "pending", "draft", "approved", "rejected", "offline"}:
        q = db.query(Post)
        if status != "all":
            q = q.filter(Post.review_status == status)
        if start_dt:
            q = q.filter(Post.created_at >= start_dt)
        if end_dt:
            q = q.filter(Post.created_at < end_dt)
        for p in q.all():
            created = p.created_at or now
            st = p.review_status or ("approved" if p.published else "draft")
            if st in {"pending", "draft"}:
                pending_count += 1
            if st in {"pending", "draft"} and now > created + timedelta(hours=24):
                timeout_count += 1

    if task_type in {"all", "comment"} and status in {"all", "pending", "approved", "rejected"}:
        q = db.query(Comment)
        if status != "all":
            q = q.filter(Comment.status == status)
        if start_dt:
            q = q.filter(Comment.created_at >= start_dt)
        if end_dt:
            q = q.filter(Comment.created_at < end_dt)
        for c in q.all():
            created = c.created_at or now
            if c.status == "pending":
                pending_count += 1
            if c.status == "pending" and now > created + timedelta(hours=24):
                timeout_count += 1

    if task_type in {"all", "report"} and status in {"all", "open", "closed", "approved", "offline"}:
        q = db.query(PostReport)
        if status == "open":
            q = q.filter(PostReport.reviewed == False)  # noqa: E712
        elif status == "closed":
            q = q.filter(PostReport.reviewed == True)  # noqa: E712
        elif status != "all":
            q = q.filter(PostReport.reviewed == (status in {"approved", "offline"}))
        if start_dt:
            q = q.filter(PostReport.created_at >= start_dt)
        if end_dt:
            q = q.filter(PostReport.created_at < end_dt)
        for r in q.all():
            created = r.created_at or now
            if not r.reviewed:
                pending_count += 1
            if (not r.reviewed) and now > created + timedelta(hours=24):
                timeout_count += 1

    processed_today = (
        db.query(WorkflowAudit)
        .filter(
            WorkflowAudit.action.in_(["approve", "reject", "offline"]),
            WorkflowAudit.created_at >= today_start,
        )
        .count()
    )
    audits = (
        db.query(WorkflowAudit)
        .filter(WorkflowAudit.action.in_(["approve", "reject", "offline"]))
        .order_by(WorkflowAudit.created_at.desc())
        .limit(300)
        .all()
    )
    durations: list[float] = []
    for a in audits:
        source_created = None
        if a.task_type == "post":
            p = db.query(Post.created_at).filter(Post.id == a.biz_id).first()
            source_created = p[0] if p else None
        elif a.task_type == "comment":
            c = db.query(Comment.created_at).filter(Comment.id == a.biz_id).first()
            source_created = c[0] if c else None
        elif a.task_type == "report":
            r = db.query(PostReport.created_at).filter(PostReport.id == a.biz_id).first()
            source_created = r[0] if r else None
        if source_created and a.created_at and a.created_at >= source_created:
            durations.append((a.created_at - source_created).total_seconds() / 3600)

    avg_hours = round(sum(durations) / len(durations), 2) if durations else 0.0
    return {
        "pending_count": int(pending_count),
        "timeout_count": int(timeout_count),
        "processed_today": int(processed_today),
        "avg_process_hours": float(avg_hours),
    }


@router.post("/tasks/batch-action")
def batch_action(
    payload: WorkflowBatchActionIn,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    if not _can_view_workflow(db, _.id):
        raise HTTPException(status_code=403, detail="forbidden")
    if payload.action not in _BATCH_ACTIONS:
        raise HTTPException(status_code=400, detail=f"invalid action: {payload.action}")
    if payload.action == "reassign" and (payload.assignee_id is None or payload.assignee_id <= 0):
        raise HTTPException(status_code=400, detail="assignee_id is required for reassign")

    success_count = 0
    fail_count = 0
    details: list[dict] = []

    tpl_text = ""
    if payload.reason_template_id:
        tpl = (
            db.query(WorkflowReasonTemplate)
            .filter(WorkflowReasonTemplate.id == payload.reason_template_id, WorkflowReasonTemplate.enabled == True)  # noqa: E712
            .first()
        )
        if tpl:
            tpl_text = tpl.content
    final_remark = " ".join([x for x in [tpl_text, (payload.remark or "").strip()] if x]).strip() or None

    for task_id in payload.task_ids:
        ok = False
        msg = ""
        try:
            kind, raw_id = task_id.split(":", 1)
            biz_id = int(raw_id)
        except Exception:
            fail_count += 1
            details.append({"task_id": task_id, "ok": False, "error": "invalid task id"})
            continue

        try:
            if kind == "post":
                row = db.query(Post).filter(Post.id == biz_id).first()
                if row is None:
                    raise ValueError("post not found")
                prev_status = row.review_status
                if payload.action == "approve":
                    row.review_status = "approved"
                    row.published = True
                    if not row.published_at:
                        row.published_at = now_shanghai_naive()
                elif payload.action == "reject":
                    row.review_status = "rejected"
                elif payload.action == "offline":
                    row.review_status = "offline"
                    row.published = False
                    row.offline_at = now_shanghai_naive()
                elif payload.action == "reassign":
                    row.author_id = payload.assignee_id
                ok = True
                msg = "ok"
                db.add(
                    WorkflowAudit(
                        task_type="post",
                        biz_id=biz_id,
                        operator_id=_.id,
                        action=payload.action,
                        from_status=prev_status,
                        to_status=row.review_status,
                        remark=final_remark,
                    )
                )
            elif kind == "comment":
                row = db.query(Comment).filter(Comment.id == biz_id).first()
                if row is None:
                    raise ValueError("comment not found")
                prev_status = row.status
                if payload.action == "approve":
                    row.status = "approved"
                elif payload.action == "reject":
                    row.status = "rejected"
                elif payload.action == "offline":
                    row.status = "rejected"
                else:
                    raise ValueError("comment task does not support reassign")
                ok = True
                msg = "ok"
                db.add(
                    WorkflowAudit(
                        task_type="comment",
                        biz_id=biz_id,
                        operator_id=_.id,
                        action=payload.action,
                        from_status=prev_status,
                        to_status=row.status,
                        remark=final_remark,
                    )
                )
            elif kind == "report":
                row = db.query(PostReport).filter(PostReport.id == biz_id).first()
                if row is None:
                    raise ValueError("report not found")
                prev_status = "closed" if row.reviewed else "open"
                if payload.action in {"approve", "reject", "offline"}:
                    row.reviewed = True
                    if payload.action == "offline":
                        p = db.query(Post).filter(Post.id == row.post_id).first()
                        if p is not None:
                            p.review_status = "offline"
                            p.published = False
                            p.offline_at = now_shanghai_naive()
                else:
                    raise ValueError("report task does not support reassign")
                ok = True
                msg = "ok"
                db.add(
                    WorkflowAudit(
                        task_type="report",
                        biz_id=biz_id,
                        operator_id=_.id,
                        action=payload.action,
                        from_status=prev_status,
                        to_status="closed" if row.reviewed else "open",
                        remark=final_remark,
                    )
                )
            else:
                raise ValueError("unsupported task kind")
        except Exception as e:  # noqa: BLE001
            ok = False
            msg = str(e)

        if ok:
            success_count += 1
            details.append({"task_id": task_id, "ok": True})
        else:
            fail_count += 1
            details.append({"task_id": task_id, "ok": False, "error": msg})

    db.commit()
    return {"ok": True, "success_count": success_count, "fail_count": fail_count, "details": details}


@router.get("/reason-templates")
def list_reason_templates(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    if not _can_view_workflow(db, _.id):
        raise HTTPException(status_code=403, detail="forbidden")
    rows = (
        db.query(WorkflowReasonTemplate)
        .filter(WorkflowReasonTemplate.enabled == True)  # noqa: E712
        .order_by(WorkflowReasonTemplate.id.asc())
        .all()
    )
    return [{"id": x.id, "name": x.name, "content": x.content} for x in rows]


@router.get("/tasks/{task_id}/audits")
def get_task_audits(
    task_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    if not _can_view_workflow(db, _.id):
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        task_type, biz_id_text = task_id.split(":", 1)
        biz_id = int(biz_id_text)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="invalid task_id") from e

    operator_ids = {int(x[0]) for x in db.query(WorkflowAudit.operator_id).filter(
        WorkflowAudit.task_type == task_type, WorkflowAudit.biz_id == biz_id
    ).all()}
    name_map = {}
    if operator_ids:
        users = db.query(User.id, User.username).filter(User.id.in_(operator_ids)).all()
        name_map = {int(i): n for i, n in users}

    rows = (
        db.query(WorkflowAudit)
        .filter(WorkflowAudit.task_type == task_type, WorkflowAudit.biz_id == biz_id)
        .order_by(WorkflowAudit.created_at.desc(), WorkflowAudit.id.desc())
        .limit(100)
        .all()
    )
    return {
        "task_id": task_id,
        "records": [
            {
                "id": r.id,
                "operator_id": r.operator_id,
                "operator_name": name_map.get(int(r.operator_id), f"user-{r.operator_id}"),
                "action": r.action,
                "from_status": r.from_status,
                "to_status": r.to_status,
                "remark": r.remark,
                "created_at": r.created_at.isoformat(timespec="seconds") if r.created_at else None,
            }
            for r in rows
        ],
    }
