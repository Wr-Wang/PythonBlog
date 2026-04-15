"""流程中心：统一待办池查询（Iteration 1 - first step）。"""
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
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
    """判定用户是否具备流程中心可见权限（含超管兜底）。"""
    codes = get_user_permission_codes(db, user_id)
    return (
        user_has_permission(codes, "admin.super")
        or user_has_permission(codes, "post.workflow")
        or user_has_permission(codes, "admin.posts.view")
        or user_has_permission(codes, "admin.dashboard.view")
    )


def _compute_priority(created_at: datetime) -> str:
    """根据任务创建时长映射优先级，供前端快速着色展示。"""
    age_hours = max(0.0, (now_shanghai_naive() - created_at).total_seconds() / 3600)
    if age_hours >= 24:
        return "high"
    if age_hours >= 8:
        return "medium"
    return "low"


def _parse_date_range(start_date: str | None, end_date: str | None) -> tuple[datetime | None, datetime | None]:
    """解析日期筛选区间（右边界按次日零点处理）。"""
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


def _candidate_limit(page: int, size: int, task_type: str) -> int:
    """
    候选任务上限：
    - 分页仍在聚合后进行，但按页大小动态扩大候选窗口，避免固定 300 在深分页下截断。
    - 限制最大值防止一次拉取过多造成内存和数据库压力。
    """
    type_factor = 4 if task_type == "all" else 2
    return max(300, min(1200, page * size * type_factor))


def _classify_batch_error(msg: str) -> str:
    """将批处理异常归一为稳定错误码，便于前端分组统计。"""
    text = (msg or "").strip().lower()
    if "invalid task id" in text:
        return "INVALID_TASK_ID"
    if "not found" in text:
        return "NOT_FOUND"
    if "does not support reassign" in text:
        return "ACTION_NOT_SUPPORTED"
    if "unsupported task kind" in text:
        return "UNSUPPORTED_TASK_KIND"
    if "forbidden" in text:
        return "FORBIDDEN"
    return "UNKNOWN"


def _collect_failed_examples(details: list[dict], limit_per_code: int = 3) -> dict[str, list[str]]:
    """从失败明细中提取样本 task_id，便于前端快速定位。"""
    out: dict[str, list[str]] = {}
    for item in details:
        if item.get("ok"):
            continue
        code = str(item.get("error_code") or "UNKNOWN")
        bucket = out.setdefault(code, [])
        if len(bucket) >= limit_per_code:
            continue
        task_id = str(item.get("task_id") or "")
        if task_id:
            bucket.append(task_id)
    return out


class WorkflowBatchActionIn(BaseModel):
    """批量流程操作入参：任务集合、动作、模板、转派与备注。"""
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
    """统一任务池查询：聚合 post/comment/report 并在内存分页。"""
    if task_type not in _TASK_TYPES:
        raise HTTPException(status_code=400, detail=f"invalid task_type: {task_type}")
    if status not in _TASK_STATUSES:
        raise HTTPException(status_code=400, detail=f"invalid status: {status}")
    if not _can_view_workflow(db, _.id):
        raise HTTPException(status_code=403, detail="forbidden")

    start_dt, end_dt = _parse_date_range(start_date, end_date)
    candidate_limit = _candidate_limit(page, size, task_type)

    tasks: list[dict] = []
    kw = (keyword or "").strip()

    if task_type in {"all", "post"}:
        # 文章任务：审核状态来自 review_status，兼容已发布但无状态的历史数据。
        q = db.query(Post, User.username).outerjoin(User, User.id == Post.author_id)
        if status != "all":
            q = q.filter(Post.review_status == status)
        if kw:
            q = q.filter(Post.title.contains(kw))
        if start_dt:
            q = q.filter(Post.created_at >= start_dt)
        if end_dt:
            q = q.filter(Post.created_at < end_dt)
        rows = q.order_by(Post.created_at.desc()).limit(candidate_limit).all()
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
        # 评论任务：以评论状态为准，标题用“评论@文章名”增强可读性。
        q = db.query(Comment, Post.title).outerjoin(Post, Post.id == Comment.post_id)
        if status != "all":
            q = q.filter(Comment.status == status)
        if kw:
            q = q.filter(Comment.content.contains(kw))
        if start_dt:
            q = q.filter(Comment.created_at >= start_dt)
        if end_dt:
            q = q.filter(Comment.created_at < end_dt)
        rows = q.order_by(Comment.created_at.desc()).limit(candidate_limit).all()
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
        # 举报任务：reviewed=False 视作 open，True 视作 closed。
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
        rows = q.order_by(PostReport.created_at.desc()).limit(candidate_limit).all()
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

    # 三类任务合流后再统一按创建时间倒序，确保跨类型排序稳定。
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
    """SLA 汇总：待处理、超时、今日处理、平均处理时长。"""
    if task_type not in _TASK_TYPES:
        raise HTTPException(status_code=400, detail=f"invalid task_type: {task_type}")
    if status not in _TASK_STATUSES:
        raise HTTPException(status_code=400, detail=f"invalid status: {status}")
    if not _can_view_workflow(db, _.id):
        raise HTTPException(status_code=403, detail="forbidden")

    start_dt, end_dt = _parse_date_range(start_date, end_date)
    now = now_shanghai_naive()
    timeout_line = now - timedelta(hours=24)
    today_start = datetime(now.year, now.month, now.day)
    pending_count = 0
    timeout_count = 0

    if task_type in {"all", "post"} and status in {"all", "pending", "draft", "approved", "rejected", "offline"}:
        # 草稿和待审都属于“待处理”口径。
        q = db.query(Post)
        if status != "all":
            q = q.filter(Post.review_status == status)
        if start_dt:
            q = q.filter(Post.created_at >= start_dt)
        if end_dt:
            q = q.filter(Post.created_at < end_dt)
        post_pending_q = q.filter(or_(Post.review_status == "pending", Post.review_status == "draft"))
        pending_count += int(post_pending_q.count() or 0)
        timeout_count += int(post_pending_q.filter(Post.created_at < timeout_line).count() or 0)

    if task_type in {"all", "comment"} and status in {"all", "pending", "approved", "rejected"}:
        # 评论仅 pending 算待处理，其余视作已处理。
        q = db.query(Comment)
        if status != "all":
            q = q.filter(Comment.status == status)
        if start_dt:
            q = q.filter(Comment.created_at >= start_dt)
        if end_dt:
            q = q.filter(Comment.created_at < end_dt)
        comment_pending_q = q.filter(Comment.status == "pending")
        pending_count += int(comment_pending_q.count() or 0)
        timeout_count += int(comment_pending_q.filter(Comment.created_at < timeout_line).count() or 0)

    if task_type in {"all", "report"} and status in {"all", "open", "closed", "approved", "offline"}:
        # 举报待处理口径为 reviewed=False。
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
        report_pending_q = q.filter(PostReport.reviewed == False)  # noqa: E712
        pending_count += int(report_pending_q.count() or 0)
        timeout_count += int(report_pending_q.filter(PostReport.created_at < timeout_line).count() or 0)

    # 今日处理量直接从审计流水统计，避免依赖各业务表状态推断。
    processed_today = (
        db.query(WorkflowAudit)
        .filter(
            WorkflowAudit.action.in_(["approve", "reject", "offline"]),
            WorkflowAudit.created_at >= today_start,
        )
        .count()
    )
    # 近 300 条审计用于估算平均处理时长，兼顾精度与查询成本。
    audits = (
        db.query(WorkflowAudit)
        .filter(WorkflowAudit.action.in_(["approve", "reject", "offline"]))
        .order_by(WorkflowAudit.created_at.desc())
        .limit(300)
        .all()
    )
    # 批量拉取源对象 created_at，避免逐条按任务类型回表（N+1）。
    post_ids = {int(a.biz_id) for a in audits if a.task_type == "post"}
    comment_ids = {int(a.biz_id) for a in audits if a.task_type == "comment"}
    report_ids = {int(a.biz_id) for a in audits if a.task_type == "report"}
    post_created_map = {
        int(i): c
        for i, c in db.query(Post.id, Post.created_at).filter(Post.id.in_(list(post_ids))).all()
    } if post_ids else {}
    comment_created_map = {
        int(i): c
        for i, c in db.query(Comment.id, Comment.created_at).filter(Comment.id.in_(list(comment_ids))).all()
    } if comment_ids else {}
    report_created_map = {
        int(i): c
        for i, c in db.query(PostReport.id, PostReport.created_at).filter(PostReport.id.in_(list(report_ids))).all()
    } if report_ids else {}
    durations: list[float] = []
    for a in audits:
        source_created = None
        if a.task_type == "post":
            source_created = post_created_map.get(int(a.biz_id))
        elif a.task_type == "comment":
            source_created = comment_created_map.get(int(a.biz_id))
        elif a.task_type == "report":
            source_created = report_created_map.get(int(a.biz_id))
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
    """批量执行流程动作；逐任务 savepoint，失败不影响其他任务。"""
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
    # 模板内容与手工备注拼接成最终审计备注，便于追溯。
    final_remark = " ".join([x for x in [tpl_text, (payload.remark or "").strip()] if x]).strip() or None

    for task_id in payload.task_ids:
        ok = False
        msg = ""
        try:
            kind, raw_id = task_id.split(":", 1)
            biz_id = int(raw_id)
        except Exception:
            fail_count += 1
            details.append(
                {
                    "task_id": task_id,
                    "ok": False,
                    "error": "invalid task id",
                    "error_code": "INVALID_TASK_ID",
                }
            )
            continue

        try:
            # 每条任务使用 savepoint，单条失败仅回滚该条，避免批处理中间失败污染其他成功任务。
            with db.begin_nested():
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
            # 收敛异常为字符串，交由 error_code 分类器做前端可消费的稳定标签。
            ok = False
            msg = str(e)

        if ok:
            success_count += 1
            details.append({"task_id": task_id, "ok": True})
        else:
            fail_count += 1
            details.append(
                {
                    "task_id": task_id,
                    "ok": False,
                    "error": msg,
                    "error_code": _classify_batch_error(msg),
                }
            )

    # 统一提交成功变更；失败项已在 savepoint 里隔离回滚。
    db.commit()
    return {
        "ok": True,
        "success_count": success_count,
        "fail_count": fail_count,
        "details": details,
        "failed_examples": _collect_failed_examples(details),
    }


@router.get("/reason-templates")
def list_reason_templates(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    """返回启用中的审核意见模板列表。"""
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
    """查询单任务审计流水，附带操作人名称映射。"""
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
