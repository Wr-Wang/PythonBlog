"""
文章领域服务：后台序列化、标签同步、分类存在性校验。

从路由层拆出，便于单测与复用，路由文件只负责 HTTP 与依赖注入。
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Category, Post, Tag
from app.schemas import PostAdminOut


def serialize_post_admin(post: Post) -> PostAdminOut:
    """ORM Post → 后台列表/详情用的 Pydantic 模型（补 category_name、tag_ids）。"""
    return PostAdminOut(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        content=post.content,
        published=post.published,
        cover_image_url=post.cover_image_url,
        created_at=post.created_at,
        updated_at=post.updated_at,
        author_id=post.author_id,
        author_name=post.author.username if post.author else None,
        category_id=post.category_id,
        category_name=post.category_rel.name if post.category_rel else None,
        tag_ids=[t.id for t in post.tags],
    )


def set_post_tags(db: Session, post: Post, tag_ids: list[int] | None) -> None:
    """
    根据 id 列表重写 post.tags；None 表示调用方未传该字段，不修改现有关联。
    传 [] 则清空标签。
    """
    if tag_ids is None:
        return
    uniq = list(dict.fromkeys(tag_ids))
    if not uniq:
        post.tags = []
        return
    tags = db.query(Tag).filter(Tag.id.in_(uniq)).all()
    if len(tags) != len(uniq):
        raise HTTPException(status_code=400, detail="存在无效的标签 id")
    post.tags = tags


def ensure_category_exists(db: Session, category_id: int | None) -> None:
    """category_id 非空时必须在 categories 表存在。"""
    if category_id is None:
        return
    c = db.query(Category).filter(Category.id == category_id).first()
    if c is None:
        raise HTTPException(status_code=400, detail="分类不存在")
