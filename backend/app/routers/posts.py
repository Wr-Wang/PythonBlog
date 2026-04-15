"""
文章 HTTP 路由：公开列表/详情、后台 CRUD。

领域逻辑见 app.services.post_service。
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.content_sanitize import sanitize_post_content
from app.database import get_db
from app.datetime_utils import now_shanghai_naive
from app.deps import get_current_user, get_user_data_scope, get_user_permission_codes, require_permission, user_has_permission
from app.models import Post, User
from app.models.ops import FeatureFlag, SearchHotword, SearchSynonym
from app.schemas import (
    PostAdminListResponse,
    PostAdminOut,
    PostCreate,
    PostListItem,
    PostOut,
    PostUpdate,
)
from app.services.post_service import ensure_category_exists, serialize_post_admin, set_post_tags
from app.services.audit_service import write_audit

router = APIRouter(prefix="/api/posts", tags=["posts"])


def _search_like_escape(s: str) -> str:
    """LIKE 通配符转义（SQL Server ESCAPE '\\'）。"""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_").replace("[", "\\[")


@router.get("/search", response_model=list[PostListItem])
def search_posts(
    db: Annotated[Session, Depends(get_db)],
    q: str = Query(..., min_length=1, max_length=200),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """站内搜索：仅已发布文章，匹配标题或摘要（SRCH-01）。"""
    q_clean = q.strip()
    if q_clean:
        hot = db.query(SearchHotword).filter(SearchHotword.keyword == q_clean).first()
        if hot is None:
            hot = SearchHotword(keyword=q_clean, cnt=1)
            db.add(hot)
        else:
            hot.cnt = int(hot.cnt or 0) + 1
        db.flush()
    syn = db.query(SearchSynonym).filter(SearchSynonym.src == q_clean, SearchSynonym.enabled == True).first()  # noqa: E712
    q_final = syn.dst if syn and syn.dst else q_clean
    term = _search_like_escape(q_final)
    pat = f"%{term}%"
    rows = (
        db.query(Post)
        .filter(
            Post.published == True,  # noqa: E712
            or_(Post.title.like(pat, escape="\\"), Post.excerpt.like(pat, escape="\\")),
        )
        .order_by(Post.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    db.commit()
    return rows


@router.get("/recommend", response_model=list[PostListItem])
def recommend_posts(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(10, ge=1, le=50),
):
    flag = db.query(FeatureFlag).filter(FeatureFlag.code == "recommendation.rule_based").first()
    if flag is not None and not flag.enabled:
        return []
    return (
        db.query(Post)
        .filter(Post.published == True)  # noqa: E712
        .order_by(Post.is_pinned.desc(), Post.weight.desc(), Post.hot_score.desc(), Post.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("", response_model=list[PostListItem])
def list_posts(
    db: Annotated[Session, Depends(get_db)],
    published_only: bool = Query(True, description="公开列表仅显示已发布"),
    sort: str = Query("time", description="time/hot/weight/editorial"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    q = db.query(Post).options(joinedload(Post.author))
    if published_only:
        q = q.filter(Post.published == True)  # noqa: E712
    if sort == "hot":
        q = q.order_by(Post.hot_score.desc(), Post.view_count.desc(), Post.created_at.desc())
    elif sort == "weight":
        q = q.order_by(Post.weight.desc(), Post.rank_level.desc(), Post.created_at.desc())
    elif sort == "editorial":
        q = q.order_by(Post.is_pinned.desc(), Post.is_featured.desc(), Post.created_at.desc())
    else:
        q = q.order_by(Post.created_at.desc())
    return q.offset(skip).limit(limit).all()


@router.get("/admin", response_model=PostAdminListResponse)
def list_all_posts(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("admin.posts.view"))],
    q: str | None = Query(None, description="关键词，匹配标题/slug/摘要"),
    review_status: str | None = Query(None),
    published: bool | None = Query(None),
    category_id: int | None = Query(None, ge=1),
    tag_id: int | None = Query(None, ge=1),
    is_pinned: bool | None = Query(None),
    is_featured: bool | None = Query(None),
    sort_by: str = Query("created_at", description="created_at/hot_score/weight/view_count/published_at"),
    sort_dir: str = Query("desc", description="asc/desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    base_q = db.query(Post)
    scope = get_user_data_scope(db, current.id)
    if scope == "self":
        base_q = base_q.filter(Post.author_id == current.id)
    if q:
        term = _search_like_escape(q.strip())
        pat = f"%{term}%"
        base_q = base_q.filter(
            or_(
                Post.title.like(pat, escape="\\"),
                Post.slug.like(pat, escape="\\"),
                Post.excerpt.like(pat, escape="\\"),
            )
        )
    if review_status:
        base_q = base_q.filter(Post.review_status == review_status)
    if published is not None:
        base_q = base_q.filter(Post.published == published)
    if category_id is not None:
        base_q = base_q.filter(Post.category_id == category_id)
    if tag_id is not None:
        base_q = base_q.filter(Post.tags.any(id=tag_id))
    if is_pinned is not None:
        base_q = base_q.filter(Post.is_pinned == is_pinned)
    if is_featured is not None:
        base_q = base_q.filter(Post.is_featured == is_featured)

    total = base_q.count()
    sort_map = {
        "created_at": Post.created_at,
        "hot_score": Post.hot_score,
        "weight": Post.weight,
        "view_count": Post.view_count,
        "published_at": Post.published_at,
    }
    col = sort_map.get(sort_by, Post.created_at)
    order_col = col.asc() if sort_dir.lower() == "asc" else col.desc()
    rows = (
        base_q.options(
            joinedload(Post.author),
            joinedload(Post.category_rel),
            selectinload(Post.tags),
        )
        .order_by(Post.is_pinned.desc(), Post.is_featured.desc(), order_col, Post.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return PostAdminListResponse(
        items=[serialize_post_admin(p) for p in rows],
        total=total,
    )


@router.get("/by-slug/{slug}", response_model=PostOut)
def get_by_slug(slug: str, db: Annotated[Session, Depends(get_db)]):
    post = db.query(Post).options(joinedload(Post.author)).filter(Post.slug == slug).first()
    if post is None or not post.published:
        raise HTTPException(status_code=404, detail="文章不存在")
    return post


@router.get("/admin/{post_id}", response_model=PostAdminOut)
def admin_get_post(
    post_id: int,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("admin.posts.view"))],
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    return serialize_post_admin(post)


@router.post("", response_model=PostAdminOut, status_code=status.HTTP_201_CREATED)
def create_post(
    body: PostCreate,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("admin.posts.create"))],
):
    if db.query(Post).filter(Post.slug == body.slug).first():
        raise HTTPException(status_code=400, detail="slug 已存在")
    ensure_category_exists(db, body.category_id)
    content = sanitize_post_content(body.content)
    post = Post(
        title=body.title,
        slug=body.slug,
        excerpt=body.excerpt,
        content=content,
        published=body.published,
        review_status=body.review_status,
        author_id=current.id,
        category_id=body.category_id,
        cover_image_url=body.cover_image_url,
        rank_level=body.rank_level,
        weight=body.weight,
        is_featured=body.is_featured,
        is_pinned=body.is_pinned,
        published_at=body.published_at,
        offline_at=body.offline_at,
        content_type=body.content_type,
        source_url=body.source_url,
    )
    db.add(post)
    db.flush()
    set_post_tags(db, post, body.tag_ids)
    write_audit(
        db,
        actor=current,
        action="post.create",
        target_type="post",
        target_id=str(post.id),
        detail=post.title,
    )
    db.commit()
    db.refresh(post)
    return serialize_post_admin(post)


@router.patch("/{post_id}", response_model=PostAdminOut)
def update_post(
    post_id: int,
    body: PostUpdate,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    data = body.model_dump(exclude_unset=True)
    tag_ids = data.pop("tag_ids", None)
    if "slug" in data and data["slug"] != post.slug:
        taken = db.query(Post).filter(Post.slug == data["slug"], Post.id != post_id).first()
        if taken:
            raise HTTPException(status_code=400, detail="slug 已存在")
    if "category_id" in data:
        ensure_category_exists(db, data["category_id"])
    if "content" in data and data["content"] is not None:
        data["content"] = sanitize_post_content(data["content"])
    codes = get_user_permission_codes(db, current.id)
    needs_base_update = any(
        k in data
        for k in [
            "title",
            "slug",
            "excerpt",
            "content",
            "published",
            "category_id",
            "cover_image_url",
            "tag_ids",
            "review_status",
            "weight",
            "rank_level",
            "published_at",
            "offline_at",
            "content_type",
            "source_url",
        ]
    ) or (tag_ids is not None)
    if needs_base_update and not user_has_permission(codes, "admin.posts.update"):
        raise HTTPException(status_code=403, detail="缺少权限: admin.posts.update")
    if "is_pinned" in data and not user_has_permission(codes, "admin.posts.pin.update"):
        raise HTTPException(status_code=403, detail="缺少权限: admin.posts.pin.update")
    if "is_featured" in data and not user_has_permission(codes, "admin.posts.featured.update"):
        raise HTTPException(status_code=403, detail="缺少权限: admin.posts.featured.update")
    if "published" in data and bool(data["published"]) and not user_has_permission(codes, "admin.posts.publish.now"):
        raise HTTPException(status_code=403, detail="缺少权限: admin.posts.publish.now")
    if "published" in data and (not bool(data["published"])) and not user_has_permission(codes, "admin.posts.offline.now"):
        raise HTTPException(status_code=403, detail="缺少权限: admin.posts.offline.now")
    for k, v in data.items():
        setattr(post, k, v)
    # 若人工立即发布/下线，补齐关键时间戳
    if "published" in data and post.published and not post.published_at:
        post.published_at = now_shanghai_naive()
    if "published" in data and (not post.published):
        post.offline_at = now_shanghai_naive()
    set_post_tags(db, post, tag_ids)
    write_audit(
        db,
        actor=current,
        action="post.update",
        target_type="post",
        target_id=str(post.id),
        detail=post.title,
    )
    db.commit()
    db.refresh(post)
    return serialize_post_admin(post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[User, Depends(get_current_user)],
    _: Annotated[None, Depends(require_permission("admin.posts.delete"))],
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    write_audit(
        db,
        actor=current,
        action="post.delete",
        target_type="post",
        target_id=str(post.id),
        detail=post.title,
    )
    db.delete(post)
    db.commit()
    return None
