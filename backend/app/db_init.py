"""
数据库初始化：建表、旧表补列、种子管理员与欢迎文章。

在应用 lifespan 中调用；与 FastAPI 应用对象解耦，便于测试时单独执行。
"""
from __future__ import annotations

import random
from collections import defaultdict

import app.models  # noqa: F401 — 加载包内全部 ORM，确保 Base.metadata 含所有表

from app.auth_utils import hash_password
from app.config import settings
from app.content_sanitize import sanitize_post_content
from app.database import Base, SessionLocal, engine
from app.db_migrate import (
    ensure_comment_reject_columns,
    ensure_comment_status_column,
    ensure_comments_unicode_columns,
    ensure_posts_extra_columns,
    ensure_roles_data_scope_column,
)
from app.models import Category, Comment, Post, Tag, User
from app.models.ops import BlacklistWord, FeatureFlag, SearchSynonym, SensitiveWord
from app.models.rbac import Menu, Permission, Role, RoleMenu, RolePermission, UserRole
from app.models.workflow import WorkflowReasonTemplate

DEFAULT_CATEGORIES = [
    {"name": "技术", "slug": "tech"},
    {"name": "生活", "slug": "life"},
    {"name": "随笔", "slug": "notes"},
    {"name": "读书", "slug": "books"},
    {"name": "旅行", "slug": "travel"},
    {"name": "摄影", "slug": "photo"},
    {"name": "音乐", "slug": "music"},
    {"name": "游戏", "slug": "game"},
    {"name": "效率", "slug": "productivity"},
    {"name": "开源", "slug": "opensource"},
]

DEFAULT_TAGS = [
    {"name": "FastAPI", "slug": "fastapi"},
    {"name": "Vue", "slug": "vue"},
    {"name": "Python", "slug": "python"},
    {"name": "部署", "slug": "deploy"},
    {"name": "SQL Server", "slug": "sqlserver"},
    {"name": "CSS", "slug": "css"},
    {"name": "Docker", "slug": "docker"},
    {"name": "测试", "slug": "testing"},
    {"name": "性能", "slug": "performance"},
    {"name": "安全", "slug": "security"},
]

# 幂等标记：存在则不再批量插入演示评论（后台可见一条 status=rejected 的占位行，可自行删除后重新种子）
_SEED_COMMENTS_MARKER_AUTHOR = "__seed_marker__"
_SEED_COMMENTS_MARKER_CONTENT = "seed-demo-comments-v1"


def _ensure_demo_comments(db, user_posts: list[Post]) -> None:
    if db.query(Comment).filter(Comment.author_name == _SEED_COMMENTS_MARKER_AUTHOR).first():
        return
    posts = [p for p in user_posts if p.published]
    if not posts:
        posts = user_posts
    if not posts:
        return

    rng = random.Random(42)
    post_ids = [p.id for p in posts]
    top_by_post: defaultdict[int, list[int]] = defaultdict(list)

    authors = [
        "访客",
        "小明",
        "匿名用户",
        "老读者",
        "路过的",
        "张三",
        "李四",
        "阿伟",
        "前端练习生",
        "运维老王",
    ]
    bodies = [
        "写得清楚，收藏了。",
        "有个地方没太看懂，能再展开讲讲吗？",
        "和我想法一致，补充一点实践经验。",
        "配图不错，排版也舒服。",
        "感谢分享，已转发给朋友。",
        "这里是不是笔误？日期好像对不上。",
        "期待下一篇。",
        "我用过类似方案，坑主要在权限配置。",
        "移动端阅读体验也很好。",
        "代码片段对我帮助很大。",
        "有没有参考资料链接？",
        "测试环境 OK，生产再观察一下。",
        "思路打开了，回头试试。",
        "不同意某段结论，理由如下……",
        "沙发！",
    ]
    status_weights = (["approved"] * 7) + (["pending"] * 2) + (["rejected"] * 1)

    for i in range(100):
        pid = rng.choice(post_ids)
        parent_id = None
        tops = top_by_post[pid]
        if tops and rng.random() < 0.38:
            parent_id = rng.choice(tops)
        st = rng.choice(status_weights)
        author = rng.choice(authors)
        content = f"{rng.choice(bodies)}（#{i + 1}）"
        if rng.random() < 0.12:
            content = "😀 " + content
        c = Comment(
            post_id=pid,
            parent_id=parent_id,
            author_name=author,
            content=content,
            status=st,
        )
        db.add(c)
        db.flush()
        if parent_id is None:
            top_by_post[pid].append(c.id)

    db.add(
        Comment(
            post_id=posts[0].id,
            parent_id=None,
            author_name=_SEED_COMMENTS_MARKER_AUTHOR,
            content=_SEED_COMMENTS_MARKER_CONTENT,
            status="rejected",
        )
    )


def init_db() -> None:
    """
    - create_all：创建尚未存在的表；
    - ensure_posts_extra_columns：给旧版 posts 增加 category_id、cover_image_url；
    - 若不存在配置中的管理员用户名，则插入管理员；
    - 幂等补齐默认分类、标签与示例文章（按 slug 去重，不重复创建）。
    """
    Base.metadata.create_all(bind=engine)
    ensure_posts_extra_columns(engine)
    ensure_roles_data_scope_column(engine)
    ensure_comments_unicode_columns(engine)
    ensure_comment_status_column(engine)
    ensure_comment_reject_columns(engine)

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

        # RBAC 基础种子（幂等）
        role = db.query(Role).filter(Role.code == "super-admin").first()
        if role is None:
            role = Role(code="super-admin", name="超级管理员", data_scope="all", is_active=True)
            db.add(role)
            db.flush()
        perm_codes = [
            ("admin.super", "超级权限"),
            ("admin.users.view", "查看用户"),
            ("admin.users.create", "新增用户"),
            ("admin.users.update", "编辑用户"),
            ("admin.users.delete", "删除用户"),
            ("admin.users.bind_roles", "给用户绑定角色"),
            ("admin.roles.view", "查看角色"),
            ("admin.roles.create", "新增角色"),
            ("admin.roles.update", "编辑角色"),
            ("admin.roles.bind_permissions", "给角色绑定权限点"),
            ("admin.roles.bind_menus", "给角色绑定菜单"),
            ("admin.permissions.view", "查看权限点"),
            ("admin.menus.view", "查看菜单"),
            ("admin.menus.create", "新增菜单"),
            ("admin.menus.update", "编辑菜单"),
            ("admin.audit.view", "查看审计日志"),
            ("admin.posts.view", "查看文章后台列表"),
            ("admin.posts.create", "新增文章"),
            ("admin.posts.update", "编辑文章"),
            ("admin.posts.delete", "删除文章"),
            ("admin.posts.pin.update", "文章置顶设置"),
            ("admin.posts.featured.update", "文章精选设置"),
            ("admin.posts.publish.now", "文章立即发布"),
            ("admin.posts.offline.now", "文章立即下线"),
            ("admin.dashboard.view", "查看运营看板"),
            ("admin.dashboard.export", "导出运营趋势"),
            ("admin.flags.manage", "管理灰度开关"),
            ("admin.moderation.manage", "管理审核词库"),
            ("admin.searchops.manage", "管理搜索运营"),
            # 兼容旧权限码
            ("rbac.view", "查看权限配置（兼容）"),
            ("rbac.manage", "管理权限配置（兼容）"),
            ("post.workflow", "文章流程流转（兼容）"),
            ("audit.view", "查看审计日志（兼容）"),
        ]
        perm_ids: list[int] = []
        for code, name in perm_codes:
            p = db.query(Permission).filter(Permission.code == code).first()
            if p is None:
                p = Permission(code=code, name=name)
                db.add(p)
                db.flush()
            perm_ids.append(p.id)
        menu_defs = [
            ("admin.posts", "文章", "/admin/posts", 10),
            ("admin.categories", "分类", "/admin/categories", 20),
            ("admin.tags", "标签", "/admin/tags", 30),
            ("admin.users", "用户", "/admin/users", 40),
            ("admin.comments", "评论", "/admin/comments", 50),
            ("admin.dashboard", "运营看板", "/admin/dashboard", 60),
            ("admin.workflow", "流程中心", "/admin/workflow", 70),
            ("admin.rbac", "权限管理", "/admin/permissions", 80),
        ]
        menu_ids: list[int] = []
        for code, name, route, order_no in menu_defs:
            m = db.query(Menu).filter(Menu.code == code).first()
            if m is None:
                m = Menu(code=code, name=name, route=route, order_no=order_no, hidden=False)
                db.add(m)
                db.flush()
            menu_ids.append(m.id)
        if not db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == role.id).first():
            db.add(UserRole(user_id=user.id, role_id=role.id))
        for pid in perm_ids:
            if not db.query(RolePermission).filter(
                RolePermission.role_id == role.id, RolePermission.permission_id == pid
            ).first():
                db.add(RolePermission(role_id=role.id, permission_id=pid))
        for mid in menu_ids:
            if not db.query(RoleMenu).filter(RoleMenu.role_id == role.id, RoleMenu.menu_id == mid).first():
                db.add(RoleMenu(role_id=role.id, menu_id=mid))

        # 运营底座种子
        if db.query(FeatureFlag).filter(FeatureFlag.code == "recommendation.rule_based").first() is None:
            db.add(
                FeatureFlag(
                    code="recommendation.rule_based",
                    name="规则推荐",
                    enabled=True,
                    rollout_percent=100,
                )
            )
        if db.query(FeatureFlag).filter(FeatureFlag.code == "search.ops").first() is None:
            db.add(FeatureFlag(code="search.ops", name="搜索运营", enabled=True, rollout_percent=100))
        # 评论审核敏感词（命中则进入 pending；未命中直接通过）
        for w in [
            "违禁词",
            "辱骂词",
            "傻X",
            "傻逼",
            "脑残",
            "滚出去",
            "去死",
            "废物",
            "狗东西",
            "畜生",
            "贱人",
            "有病吧",
            "诈骗",
            "博彩",
            "赌博",
            "代开发票",
            "办证",
            "洗钱",
            "黄赌毒",
            "色情",
            "成人交易",
            "约炮",
            "一夜情",
            "成人视频",
            "兼职刷单",
            "返利骗局",
            "高回报稳赚",
            "躺赚",
            "秒到账",
            "外挂",
            "木马",
            "钓鱼网站",
            "免实名",
            "跑分",
            "黑客接单",
            "社工库",
            "网赚",
            "引流",
            "加V私聊",
            "VX联系",
            "QQ私聊",
            "Telegram群",
            "飞机群",
        ]:
            if db.query(SensitiveWord).filter(SensitiveWord.word == w).first() is None:
                db.add(SensitiveWord(word=w, enabled=True))
        for w in ["spam", "刷屏"]:
            if db.query(BlacklistWord).filter(BlacklistWord.word == w).first() is None:
                db.add(BlacklistWord(word=w, enabled=True))
        if db.query(SearchSynonym).filter(SearchSynonym.src == "ai", SearchSynonym.dst == "人工智能").first() is None:
            db.add(SearchSynonym(src="ai", dst="人工智能", enabled=True))
        reason_templates = [
            ("事实性错误", "存在事实性错误，需修订后重提。"),
            ("质量不达标", "内容质量未达发布标准，请补充案例与论证。"),
            ("合规风险", "存在潜在合规风险，请调整措辞并补充来源说明。"),
        ]
        for name, content in reason_templates:
            if db.query(WorkflowReasonTemplate).filter(WorkflowReasonTemplate.name == name).first() is None:
                db.add(WorkflowReasonTemplate(name=name, content=content, enabled=True))

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
                content=sanitize_post_content(content),
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
        ensure_post(
            title="富文本示例：排版与嵌入视频",
            slug="rich-editor-demo",
            excerpt="图文、列表与在线视频嵌入示例（后台富文本）。",
            content=(
                "<p>本篇为<strong>富文本 HTML</strong>示例，支持<em>强调</em>与列表。</p>"
                "<h2>使用说明</h2>"
                "<ul>"
                "<li>图片：工具栏「图片」上传后插入；</li>"
                "<li>视频：工具栏「视频」粘贴 YouTube / B 站等嵌入链接。</li>"
                "</ul>"
                "<p>下方为示例嵌入（若网络限制可能无法播放）：</p>"
                '<p><iframe width="560" height="315" '
                'src="https://www.youtube.com/embed/dQw4w9WgXcQ" '
                'title="示例视频" frameborder="0" allowfullscreen></iframe></p>'
                "<p>表情：😀 🎉 ✨</p>"
            ),
            published=True,
            category_slug="tech",
            tag_slugs=["vue", "fastapi"],
        )
        ensure_post(
            title="富文本：外链图片与超链接",
            slug="rich-images-links",
            excerpt="正文中图片与外部链接的展示效果。",
            content=(
                "<p>以下为占位图（HTTPS 外链），用于验证正文内图片样式：</p>"
                '<p><img src="https://picsum.photos/seed/pythonblog/720/360" '
                'alt="示例配图" /></p>'
                "<p>文档链接："
                '<a href="https://fastapi.tiangolo.com/" target="_blank" '
                'rel="noopener noreferrer">FastAPI 文档</a>'
                "</p>"
            ),
            published=True,
            category_slug="life",
            tag_slugs=["python", "deploy"],
        )
        ensure_post(
            title="异步 Python：并发与可维护性",
            slug="async-python-notes",
            excerpt="在 I/O 密集场景下使用 async/await 的一点体会与注意事项。",
            content=(
                "## 何时考虑异步\n\n"
                "当瓶颈在网络或数据库等待时，异步能减少线程占用；CPU 密集仍要交给进程或多机。\n\n"
                "## 可维护性\n\n"
                "保持函数短小、错误路径清晰，比盲目堆 `gather` 更重要。"
            ),
            published=True,
            category_slug="tech",
            tag_slugs=["python", "performance"],
        )
        ensure_post(
            title="Vue 组合式 API 速记",
            slug="vue-composition-api-tips",
            excerpt="从选项式迁到组合式时常见的模式与踩坑。",
            content=(
                "## 组合式要点\n\n"
                "- `ref` / `reactive` 选用习惯要统一；\n"
                "- 大块逻辑抽到 `useXxx` 便于复测；\n"
                "- 与 TypeScript 配合时注意推导类型。\n\n"
                "小步重构比一次性大改风险更低。"
            ),
            published=True,
            category_slug="tech",
            tag_slugs=["vue", "css"],
        )
        ensure_post(
            title="SQL Server 索引排查手记",
            slug="sqlserver-indexing-tips",
            excerpt="慢查询日志、缺失索引与执行计划阅读顺序。",
            content=(
                "## 排查顺序\n\n"
                "1. 确认真实参数与基数估计；\n"
                "2. 看是否出现意外扫描；\n"
                "3. 再考虑新增或调整索引。\n\n"
                "索引不是越多越好，写入成本要一起评估。"
            ),
            published=True,
            category_slug="opensource",
            tag_slugs=["sqlserver", "performance"],
        )
        ensure_post(
            title="周末徒步：路线与装备清单",
            slug="weekend-hiking-checklist",
            excerpt="一日轻装路线示例，以及个人会带的应急小物。",
            content=(
                "## 路线\n\n"
                "选成熟步道，提前看天气与关门时间。\n\n"
                "## 装备\n\n"
                "水、头灯、薄外套、简单急救包；手机离线地图提前下好。"
            ),
            published=True,
            category_slug="travel",
            tag_slugs=["docker", "security"],
        )
        ensure_post(
            title="2026 开年书单（技术向）",
            slug="reading-list-2026",
            excerpt="系统设计与工程实践类书目，按阅读顺序排列。",
            content=(
                "## 书单\n\n"
                "- 分布式系统基础；\n"
                "- 软件架构权衡；\n"
                "- 一本与团队流程相关的轻量读物。\n\n"
                "读不完也没关系，挑一两本精读更有效。"
            ),
            published=True,
            category_slug="books",
            tag_slugs=["python", "testing"],
        )

        db.flush()
        seed_posts = db.query(Post).order_by(Post.id.asc()).all()
        _ensure_demo_comments(db, seed_posts)

        db.commit()
    finally:
        db.close()
