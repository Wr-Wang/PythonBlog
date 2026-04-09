"""
将数据库中标题重复的文章改为互不相同：按 id 升序，首篇保留原标题，
后续重复篇在标题末尾追加随机数字后缀（保证 ≤255 字、全局唯一）。

用法（在 backend 目录下）:
  python scripts/dedupe_post_titles.py
  python scripts/dedupe_post_titles.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import app.models  # noqa: F401

from app.database import SessionLocal
from app.models import Post

_TITLE_MAX = 255


def _make_unique_title(base: str, used: set[str], post_id: int) -> str:
    b = (base or "").strip()
    for _ in range(120):
        suf = f"·{secrets.randbelow(900_000) + 100_000}"
        max_base = _TITLE_MAX - len(suf)
        if max_base < 1:
            b = str(post_id)
            max_base = _TITLE_MAX - len(suf)
        candidate = (b[:max_base] + suf).strip()
        if candidate not in used and len(candidate) <= _TITLE_MAX:
            return candidate
    fallback = f"{b[:230]}·{post_id}"[:_TITLE_MAX]
    if fallback not in used:
        return fallback
    return f"{b[:220]}·{post_id}·{secrets.token_hex(3)}"[:_TITLE_MAX]


def run(*, dry_run: bool) -> int:
    db = SessionLocal()
    changed = 0
    try:
        posts = db.query(Post).order_by(Post.id.asc()).all()
        used_titles: set[str] = set()
        for p in posts:
            t = (p.title or "").strip()
            if t not in used_titles:
                used_titles.add(t)
                continue
            new_t = _make_unique_title(t, used_titles, p.id)
            print(f"id={p.id} slug={p.slug!r}\n  旧: {t}\n  新: {new_t}")
            if not dry_run:
                p.title = new_t
            used_titles.add(new_t)
            changed += 1
        if dry_run:
            print(f"[dry-run] 将修改 {changed} 条，未写入数据库。")
        else:
            db.commit()
            print(f"已更新 {changed} 条文章标题。")
        return changed
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="随机重命名重复的文章标题")
    ap.add_argument("--dry-run", action="store_true", help="只打印不提交")
    args = ap.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
