"""
评论领域服务：后台列表行组装（附带文章标题）。
"""
from app.models import Comment
from app.schemas import CommentAdminOut


def comment_to_admin_out(comment: Comment, post_title: str) -> CommentAdminOut:
    """单条评论 ORM + 文章标题 → CommentAdminOut。"""
    return CommentAdminOut(
        id=comment.id,
        post_id=comment.post_id,
        post_title=post_title,
        parent_id=comment.parent_id,
        author_name=comment.author_name,
        content=comment.content,
        status=comment.status,
        created_at=comment.created_at,
    )
