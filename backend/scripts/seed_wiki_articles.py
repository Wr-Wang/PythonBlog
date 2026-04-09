"""
从中文维基百科开放 API 拉取随机条目摘要，生成 100 篇互不相同的正文（CC BY-SA，正文内附来源说明），
并为每篇生成 5～100 条不等、可多层嵌套的评论。

用法（在 backend 目录下）:
  python scripts/seed_wiki_articles.py --replace

--replace 会删除 slug 为 wiki-seed-* 与 bulk-seed-* 的旧种子文章（级联删除其评论），再写入新数据。
需能访问 zh.wikipedia.org；若部分请求失败，将用本地占位段落补齐，保证仍为 100 篇且内容互异。

User-Agent 须合规，见: https://meta.wikimedia.org/wiki/User-Agent_policy
"""
from __future__ import annotations

import argparse
import html
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

# 保证可 import app
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import app.models  # noqa: F401

from sqlalchemy import or_

from app.content_sanitize import sanitize_post_content
from app.database import SessionLocal
from app.models import Category, Comment, Post, Tag, User

WIKI_API = "https://zh.wikipedia.org/w/api.php"
WIKI_UA = "PythonBlogSeed/1.0 (educational local seed; urllib) Python"

_SLUG_PREFIX_WIKI = "wiki-seed-"
_SLUG_PREFIX_LEGACY = "bulk-seed-"


def _request_json(url: str, timeout: float = 45.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def fetch_random_titles(count: int = 100) -> list[str]:
    """MediaWiki API: list=random，一次最多 500。"""
    qs = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "list": "random",
            "rnnamespace": "0",
            "rnlimit": str(min(count, 500)),
        }
    )
    url = f"{WIKI_API}?{qs}"
    data = _request_json(url)
    items = data.get("query", {}).get("random", [])
    return [x["title"] for x in items if x.get("title")]


def fetch_summary(title: str) -> dict | None:
    safe = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"https://zh.wikipedia.org/api/rest_v1/page/summary/{safe}"
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
    try:
        with urllib.request.urlopen(req, timeout=45.0) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        return None
    except OSError:
        return None


def _extract_to_html(extract: str) -> str:
    parts = [p.strip() for p in extract.replace("\r\n", "\n").split("\n") if p.strip()]
    out = []
    for p in parts:
        out.append(f"<p>{html.escape(p)}</p>")
    return "\n".join(out) if out else "<p>（无摘要文本）</p>"


def build_post_html(summary: dict, fallback_index: int) -> tuple[str, str, str]:
    """返回 (title, excerpt, html_content)。"""
    title = (summary or {}).get("title") or f"维基摘要占位·{fallback_index}"
    if len(title) > 255:
        title = title[:252] + "…"

    extract = (summary or {}).get("extract") or ""
    page_url = (
        (summary or {}).get("content_urls", {}).get("desktop", {}).get("page")
        or f"https://zh.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
    )

    thumb = (summary or {}).get("thumbnail", {}) or {}
    thumb_src = thumb.get("source")
    if thumb_src and not str(thumb_src).lower().startswith("https:"):
        thumb_src = None

    if not extract.strip():
        extract = (
            f"条目「{title}」暂无摘要文本（API 未返回或为重定向页）。"
            f"索引 #{fallback_index}，用于本地演示数据。"
        )

    body_parts = []
    if thumb_src:
        body_parts.append(
            f'<p><img src="{html.escape(thumb_src)}" alt="{html.escape(title)}" /></p>'
        )
    body_parts.append(_extract_to_html(extract))
    body_parts.append(
        "<p><em>摘要来源：中文维基百科，"
        f'<a href="{html.escape(page_url)}" target="_blank" rel="noopener noreferrer">'
        "查看原文</a>（内容以 CC BY-SA 4.0 授权；本页为摘录展示）。"
        "</em></p>"
    )
    raw = "\n".join(body_parts)
    excerpt = extract.replace("\n", " ").strip()
    if len(excerpt) > 500:
        excerpt = excerpt[:497] + "…"
    return title, excerpt, raw


def fallback_summary(index: int) -> dict:
    """网络失败时的互异占位（与索引绑定）。标题仅保留原「括号内」主题词，如「记录跨学科视角」。"""
    rng = random.Random(index * 7919 + 42)
    verbs = ["探讨", "回顾", "梳理", "简述", "记录", "分析"]
    topics = ["概念史", "技术脉络", "公共记忆", "跨学科视角", "实践案例", "方法论"]
    return {
        "title": f"{rng.choice(verbs)}{rng.choice(topics)}",
        "extract": (
            f"第 {index} 条本地生成的占位摘要，用于在网络不可用时仍保持篇目互不重复。"
            f"随机种子 {rng.randint(1000, 9999)}；段落仅作排版与列表测试，不代表真实观点。"
            "\n\n"
            "说明：重新联网并执行本脚本可替换为真实维基摘要。"
        ),
        "content_urls": {"desktop": {"page": "https://zh.wikipedia.org"}},
        "thumbnail": None,
    }


_OFFLINE_TITLE_RE = re.compile(r"^离线占位条目·第\d+篇（(.+)）$")


def normalize_existing_offline_titles(db) -> int:
    """将已入库的旧格式标题「离线占位条目·第N篇（xxx）」改为仅「xxx」。"""
    n = 0
    for p in db.query(Post).all():
        m = _OFFLINE_TITLE_RE.match((p.title or "").strip())
        if m:
            p.title = m.group(1).strip()
            if len(p.title) > 255:
                p.title = p.title[:252] + "…"
            n += 1
    return n


def delete_seed_posts(db) -> int:
    """删除 wiki-seed-* 与 bulk-seed-* 文章（评论随 posts 级联删除）。"""
    q = db.query(Post).filter(
        or_(
            Post.slug.like(f"{_SLUG_PREFIX_WIKI}%"),
            Post.slug.like(f"{_SLUG_PREFIX_LEGACY}%"),
        )
    )
    n = q.count()
    q.delete(synchronize_session=False)
    return n


def _collect_random_titles() -> list[str]:
    titles: list[str] = []
    seen_t: set[str] = set()
    while len(titles) < 100:
        batch = fetch_random_titles(min(100, 500 - len(titles)))
        for t in batch:
            if t not in seen_t:
                seen_t.add(t)
                titles.append(t)
            if len(titles) >= 100:
                break
        time.sleep(0.15)
    return titles[:100]


def insert_posts_and_comments(
    db,
    user: User,
    categories: list[Category],
    tags: list[Tag],
    *,
    offline: bool = False,
) -> None:
    if offline:
        titles = [f"__offline_title__{i:04d}" for i in range(1, 101)]
    else:
        try:
            titles = _collect_random_titles()
        except OSError as e:
            print(
                f"警告：无法访问维基百科 API（{e}），改用本地生成的 100 篇互异占位正文。",
                file=sys.stderr,
            )
            titles = [f"__offline_title__{i:04d}" for i in range(1, 101)]

    tag_objs = tags
    if not categories or not tag_objs:
        raise RuntimeError("数据库中需已有分类与标签（先运行 init_db）")

    summaries: list[dict | None] = [None] * 100

    offline_only = bool(titles) and titles[0].startswith("__offline_title__")
    if offline_only:
        summaries = [None] * 100
    else:

        def job(idx: int, title: str) -> tuple[int, dict | None]:
            s = fetch_summary(title)
            return idx, s

        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(job, i, t) for i, t in enumerate(titles)]
            for fut in as_completed(futs):
                idx, s = fut.result()
                summaries[idx] = s

    inserted_posts: list[Post] = []
    for i in range(100):
        slug = f"{_SLUG_PREFIX_WIKI}{i + 1:03d}"
        summ = summaries[i]
        ext = str((summ or {}).get("extract") or "").strip()
        if (
            not summ
            or not ext
            or (summ or {}).get("type") == "disambiguation"
        ):
            summ = fallback_summary(i + 1)
        title, excerpt, raw_html = build_post_html(summ, i + 1)
        content = sanitize_post_content(raw_html)

        cat = categories[i % len(categories)]
        t1 = tag_objs[i % len(tag_objs)]
        t2 = tag_objs[(i + 1) % len(tag_objs)]

        p = Post(
            title=title,
            slug=slug,
            excerpt=excerpt,
            content=content,
            published=True,
            author_id=user.id,
            category_id=cat.id,
            cover_image_url=None,
        )
        p.tags = [t1, t2]
        db.add(p)
        inserted_posts.append(p)

    db.flush()

    rng = random.Random(20260210)
    authors = [
        "摸鱼小能手",
        "周末补觉党",
        "晚风邮差",
        "读者甲",
        "路人乙",
        "潜水员",
        "追更人",
        "芋泥波波",
        "匿名网友",
        "过路点赞",
    ]
    bodies = [
        "这段摘要读下来很清晰。",
        "有没有更多延伸阅读？",
        "配图和排版在手机上也不错。",
        "同意，再补充一个角度。",
        "嵌套回复测试：子评论。",
        "想引用原文里的一句话。",
        "标记，回头细看。",
        "和百科条目对照过了，有帮助。",
        "沙发。",
        "感谢整理。",
    ]

    for p in inserted_posts:
        n_comments = rng.randint(5, 100)
        pool: list[int] = []
        for k in range(n_comments):
            parent_id = None
            if pool and rng.random() < 0.78:
                parent_id = rng.choice(pool)
            st = rng.choice((["approved"] * 7) + (["pending"] * 2) + (["rejected"] * 1))
            body = f"{rng.choice(bodies)}（#{k + 1}）"
            if rng.random() < 0.08:
                body = "😀 " + body
            c = Comment(
                post_id=p.id,
                parent_id=parent_id,
                author_name=rng.choice(authors),
                content=body,
                status=st,
            )
            db.add(c)
            db.flush()
            pool.append(c.id)


def main() -> None:
    parser = argparse.ArgumentParser(description="从维基百科摘要生成 100 篇文章与嵌套评论")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="删除 wiki-seed-* / bulk-seed-* 旧种子后再写入",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="不访问网络，全部使用本地互异占位正文（适合无外网或 API 不可达时）",
    )
    parser.add_argument(
        "--normalize-titles",
        action="store_true",
        help='将已存在标题「离线占位条目·第N篇（xxx）」批量改为仅「xxx」（不重建文章）',
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.normalize_titles:
            n = normalize_existing_offline_titles(db)
            db.commit()
            print(f"已更新 {n} 条文章标题（仅保留括号内主题词）。")
            return

        user = db.query(User).order_by(User.id.asc()).first()
        if user is None:
            print("错误：无用户，请先执行 init_db。", file=sys.stderr)
            sys.exit(1)

        categories = db.query(Category).order_by(Category.id.asc()).all()
        tags = db.query(Tag).order_by(Tag.id.asc()).all()

        if not args.replace and db.query(Post).filter(Post.slug == f"{_SLUG_PREFIX_WIKI}001").first():
            print("已存在 wiki-seed-001，跳过。如需重建请加 --replace", file=sys.stderr)
            sys.exit(0)

        if args.replace:
            deleted = delete_seed_posts(db)
            print(f"已标记删除旧种子文章 {deleted} 篇（含级联评论），即将写入新数据…")

        insert_posts_and_comments(db, user, categories, tags, offline=args.offline)
        db.commit()
        print("已写入 100 篇 wiki-seed-* 文章，并为每篇生成 5～100 条嵌套评论。")
    except Exception as e:
        db.rollback()
        print(f"失败: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
