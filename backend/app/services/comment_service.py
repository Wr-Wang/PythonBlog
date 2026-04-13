"""
评论领域服务：后台列表行组装（附带文章标题）。
"""
from app.models import Comment
from app.schemas import CommentAdminOut


def comment_to_admin_out(
    comment: Comment,
    post_title: str,
    *,
    level: int = 0,
    parent_author_name: str | None = None,
) -> CommentAdminOut:
    """单条评论 ORM + 文章标题 → CommentAdminOut。"""
    return CommentAdminOut(
        id=comment.id,
        post_id=comment.post_id,
        post_title=post_title,
        parent_id=comment.parent_id,
        level=level,
        parent_author_name=parent_author_name,
        author_name=comment.author_name,
        content=comment.content,
        status=comment.status,
        reject_type=comment.reject_type,
        reject_reason=comment.reject_reason,
        created_at=comment.created_at,
    )
