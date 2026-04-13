"""文章定时发布/下线执行器。"""
from app.datetime_utils import now_shanghai_naive
from app.models import Post
from app.services.audit_service import write_audit


def run_due_post_jobs(db) -> dict[str, int]:
    now = now_shanghai_naive()
    published_count = 0
    offline_count = 0

    due_publish = (
        db.query(Post)
        .filter(
            Post.published_at.isnot(None),
            Post.published_at <= now,
            Post.published == False,  # noqa: E712
            Post.review_status.in_(["pending", "approved", "draft"]),
        )
        .all()
    )
    for p in due_publish:
        p.published = True
        p.review_status = "approved"
        published_count += 1
        write_audit(
            db,
            actor=None,
            action="post.auto_publish",
            target_type="post",
            target_id=str(p.id),
            detail=p.title,
        )

    due_offline = (
        db.query(Post)
        .filter(
            Post.offline_at.isnot(None),
            Post.offline_at <= now,
            Post.published == True,  # noqa: E712
        )
        .all()
    )
    for p in due_offline:
        p.published = False
        p.review_status = "offline"
        offline_count += 1
        write_audit(
            db,
            actor=None,
            action="post.auto_offline",
            target_type="post",
            target_id=str(p.id),
            detail=p.title,
        )

    if published_count or offline_count:
        db.commit()

    return {"published": published_count, "offline": offline_count}
