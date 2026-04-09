"""
删除标题末尾为「·」+ 6 位随机数字的文章（与 dedupe_post_titles.py 追加的后缀一致），
并依赖数据库外键级联删除该文下的评论、post_tags 等关联数据。

用法（在 backend 目录下）:
  python scripts/delete_posts_title_numeric_suffix.py --dry-run
  python scripts/delete_posts_title_numeric_suffix.py
"""
from __future__ import annotations

import argparse
import os
import re
import sys

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import app.models  # noqa: F401

from app.database import SessionLocal
from app.models import Post

# 与 dedupe_post_titles 中 suf = f"·{secrets.randbelow(900_000) + 100_000}" 一致：六位数字
_NUM_SUFFIX = re.compile(r"·\d{6}$")


def main() -> None:
    ap = argparse.ArgumentParser(description="删除标题带 ·六位随机数 后缀的文章及级联数据")
    ap.add_argument("--dry-run", action="store_true", help="只列出将删除的条目，不执行删除")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        all_posts = db.query(Post).order_by(Post.id.asc()).all()
        targets = [p for p in all_posts if _NUM_SUFFIX.search((p.title or "").strip())]
        if not targets:
            print("没有匹配标题（末尾为 ·+6 位数字）的文章。")
            return

        print(f"将处理 {len(targets)} 篇：")
        for p in targets:
            print(f"  id={p.id} slug={p.slug!r} title={p.title!r}")

        if args.dry_run:
            print("[dry-run] 未删除。")
            return

        for p in targets:
            db.delete(p)
        db.commit()
        print(f"已删除 {len(targets)} 篇文章（评论等由数据库级联删除）。")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
