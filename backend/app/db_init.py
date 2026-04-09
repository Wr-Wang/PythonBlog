"""
数据库初始化：建表、旧表补列、种子管理员与欢迎文章。

在应用 lifespan 中调用；与 FastAPI 应用对象解耦，便于测试时单独执行。
"""
import app.models  # noqa: F401 — 加载包内全部 ORM，确保 Base.metadata 含所有表

from app.auth_utils import hash_password
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.db_migrate import ensure_comments_unicode_columns, ensure_posts_extra_columns
from app.models import Category, Post, Tag, User

DEFAULT_CATEGORIES = [
    {"name": "技术", "slug": "tech"},
    {"name": "生活", "slug": "life"},
    {"name": "随笔", "slug": "notes"},
]

DEFAULT_TAGS = [
    {"name": "FastAPI", "slug": "fastapi"},
    {"name": "Vue", "slug": "vue"},
    {"name": "Python", "slug": "python"},
    {"name": "部署", "slug": "deploy"},
]


def init_db() -> None:
    """
    - create_all：创建尚未存在的表；
    - ensure_posts_extra_columns：给旧版 posts 增加 category_id、cover_image_url；
    - 若不存在配置中的管理员用户名，则插入管理员；
    - 幂等补齐默认分类、标签与示例文章（按 slug 去重，不重复创建）。
    """
    Base.metadata.create_all(bind=engine)
    ensure_posts_extra_columns(engine)
    ensure_comments_unicode_columns(engine)

    admin_user = settings.admin_username
    admin_pass = settings.admin_password
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == admin_user).first()
        if user is None:
            user = User(
                username=admin_user,
                hashed_password=hash_password(admin_pass),
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        category_by_slug: dict[str, Category] = {}
        for item in DEFAULT_CATEGORIES:
            c = db.query(Category).filter(Category.slug == item["slug"]).first()
            if c is None:
                c = Category(name=item["name"], slug=item["slug"])
                db.add(c)
                db.flush()
            category_by_slug[item["slug"]] = c

        tag_by_slug: dict[str, Tag] = {}
        for item in DEFAULT_TAGS:
            t = db.query(Tag).filter(Tag.slug == item["slug"]).first()
            if t is None:
                t = Tag(name=item["name"], slug=item["slug"])
                db.add(t)
                db.flush()
            tag_by_slug[item["slug"]] = t

        def ensure_post(
            *,
            title: str,
            slug: str,
            excerpt: str,
            content: str,
            published: bool,
            category_slug: str | None = None,
            tag_slugs: list[str] | None = None,
        ) -> None:
            p = db.query(Post).filter(Post.slug == slug).first()
            if p is not None:
                return
            p = Post(
                title=title,
                slug=slug,
                excerpt=excerpt,
                content=content,
                published=published,
                author_id=user.id,
                category_id=category_by_slug[category_slug].id if category_slug else None,
                cover_image_url=None,
            )
            if tag_slugs:
                p.tags = [tag_by_slug[s] for s in tag_slugs if s in tag_by_slug]
            db.add(p)

        ensure_post(
            title="欢迎来到我的博客",
            slug="welcome",
            excerpt="这是第一篇示例文章。",
            content=(
                "## 你好\n\n"
                "这是使用 **Python (FastAPI)** + **Vue** + **SQL Server** 搭建的个人博客。\n\n"
                "登录后台即可编辑或删除本篇文章。"
            ),
            published=True,
            category_slug="tech",
            tag_slugs=["fastapi", "vue", "python"],
        )
        ensure_post(
            title="Windows + IIS 部署清单",
            slug="windows-iis-deploy-checklist",
            excerpt="记录从构建到发布的关键步骤，便于快速回顾。",
            content=(
                "## 部署清单\n\n"
                "1. 构建前端：`npm run build`\n"
                "2. 回收 IIS 应用程序池\n"
                "3. 检查 `/api/health` 返回是否正常\n\n"
                "建议将常见错误与排查命令写入文档，降低重复劳动。"
            ),
            published=True,
            category_slug="tech",
            tag_slugs=["deploy", "python"],
        )
        ensure_post(
            title="本周学习记录",
            slug="weekly-learning-notes",
            excerpt="关于编码习惯、重构实践与效率提升的一些心得。",
            content=(
                "## 本周总结\n\n"
                "- 提取公共方法减少重复代码\n"
                "- 优先做低风险重构\n"
                "- 重要改动后做自动化构建验证\n\n"
                "持续迭代比一次性大改更稳。"
            ),
            published=False,
            category_slug="notes",
            tag_slugs=["python"],
        )
        db.commit()
    finally:
        db.close()
