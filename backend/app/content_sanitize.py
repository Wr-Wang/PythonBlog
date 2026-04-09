"""
正文安全：
- 富文本 HTML：bleach 白名单标签/属性 + 内联样式（Quill）；再按 VID-01 校验 iframe。
- 旧版 Markdown 正文：不以 HTML 识别时跳过 bleach，仅做 iframe 清洗（兼容文中嵌入代码块里的 <）。
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

import bleach
from bleach.css_sanitizer import CSSSanitizer

# 允许嵌入的 iframe 目标主机（小写，不含端口）；含 www.youtube.com 等归一化判断
_ALLOWED_IFRAME_SUFFIXES = (
    "youtube.com",
    "youtube-nocookie.com",
    "youtu.be",
    "bilibili.com",
    "vimeo.com",
)
_ALLOWED_IFRAME_EXACT = frozenset(
    {
        "player.bilibili.com",
        "player.vimeo.com",
    }
)

_IFRAME_BLOCK = re.compile(
    r"<iframe\b[^>]*>.*?</iframe>|<iframe\b[^/>]*/>",
    re.IGNORECASE | re.DOTALL,
)

_LOOKS_LIKE_HTML_START = re.compile(r"^\s*<[!/?]?[a-zA-Z]")

_BLEACH_TAGS = frozenset(
    {
        "p",
        "br",
        "div",
        "span",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "s",
        "strike",
        "del",
        "sub",
        "sup",
        "blockquote",
        "pre",
        "code",
        "ul",
        "ol",
        "li",
        "a",
        "img",
        "iframe",
    }
)

_BLEACH_ATTRS = {
    "*": ["class"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "iframe": [
        "src",
        "width",
        "height",
        "allowfullscreen",
        "allow",
        "frameborder",
        "title",
    ],
    "span": ["style"],
    "p": ["style"],
    "div": ["style"],
    "li": ["style"],
}

_CSS_SANITIZER = CSSSanitizer()


def _looks_like_html_fragment(text: str) -> bool:
    t = text or ""
    return bool(_LOOKS_LIKE_HTML_START.match(t))


def _hostname_allowed(host: str) -> bool:
    if not host:
        return False
    h = host.lower().strip()
    if h.startswith("www."):
        h = h[4:]
    if h in _ALLOWED_IFRAME_EXACT:
        return True
    for suf in _ALLOWED_IFRAME_SUFFIXES:
        if h == suf or h.endswith("." + suf):
            return True
    return False


def _iframe_src_allowed(src: str) -> bool:
    s = (src or "").strip()
    if not s:
        return False
    low = s.lower()
    if low.startswith(("javascript:", "data:", "vbscript:")):
        return False
    if s.startswith("//"):
        s = "https:" + s
    try:
        p = urlparse(s)
    except Exception:
        return False
    if p.scheme not in ("http", "https"):
        return False
    return _hostname_allowed(p.hostname or "")


def _replace_iframe(m: re.Match) -> str:
    block = m.group(0)
    src_m = re.search(r"\bsrc\s*=\s*([\"'])([^\"']*)\1", block, re.IGNORECASE)
    if not src_m:
        return ""
    if _iframe_src_allowed(src_m.group(2)):
        return block
    return ""


def sanitize_embed_content(text: str) -> str:
    """移除非法 iframe；合法 iframe 原样保留。"""
    if not text:
        return text
    return _IFRAME_BLOCK.sub(_replace_iframe, text)


def sanitize_post_content(text: str) -> str:
    """
    文章正文入库前调用：富文本走 bleach；最后统一校验 iframe src。
    非 HTML 开头（多为 Markdown）不套 bleach，避免破坏 ``` 代码块等。
    """
    if not text:
        return text
    s = text
    if _looks_like_html_fragment(s):
        s = bleach.clean(
            s,
            tags=_BLEACH_TAGS,
            attributes=_BLEACH_ATTRS,
            css_sanitizer=_CSS_SANITIZER,
            strip=True,
            protocols=["http", "https", "mailto"],
        )
    return sanitize_embed_content(s)
