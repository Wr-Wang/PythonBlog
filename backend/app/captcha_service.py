"""
后台登录验证码：形态轮换（图形 / 算术），内存存储，一次性消费。

与 app.routers.auth 配合：同一用户名密码失败 ≥1 次后，下次登录须带有效验证码。
"""
from __future__ import annotations

import base64
import io
import random
import secrets
import string
import threading
import time

CAPTCHA_TTL_SEC = 180
LOGIN_FAIL_TTL_SEC = 900  # 15 分钟内未登录成功则清空失败计数

_lock = threading.Lock()

# 轮换计数：每次签发新验证码时切换形态
_rotate_idx = 0

# captcha_id -> {answer: str, kind: str, exp: monotonic}
_store: dict[str, dict] = {}

# username -> {failures: int, ts: monotonic}
_login_fail: dict[str, dict] = {}


def _norm_user(username: str) -> str:
    return (username or "").strip()


def _purge_stale_login() -> None:
    now = time.monotonic()
    dead = [u for u, st in _login_fail.items() if now - st["ts"] > LOGIN_FAIL_TTL_SEC]
    for u in dead:
        del _login_fail[u]


def needs_captcha_after_failed_password(username: str) -> bool:
    u = _norm_user(username)
    if not u:
        return False
    with _lock:
        _purge_stale_login()
        st = _login_fail.get(u)
        return bool(st and st.get("failures", 0) >= 1)


def record_password_failure(username: str) -> None:
    u = _norm_user(username)
    if not u:
        return
    with _lock:
        _purge_stale_login()
        st = _login_fail.get(u)
        n = (st["failures"] if st else 0) + 1
        _login_fail[u] = {"failures": n, "ts": time.monotonic()}


def clear_login_failures(username: str) -> None:
    u = _norm_user(username)
    if not u:
        return
    with _lock:
        _login_fail.pop(u, None)


def _cleanup_expired_captchas() -> None:
    now = time.monotonic()
    dead = [k for k, v in _store.items() if now > v["exp"]]
    for k in dead:
        del _store[k]


def _random_text_chars(n: int = 4) -> str:
    alphabet = string.ascii_uppercase.replace("O", "").replace("I", "") + string.digits.replace("0", "").replace("1", "")
    return "".join(random.choices(alphabet, k=n))


def _render_image_png(text: str) -> str:
    from PIL import Image, ImageDraw, ImageFont

    w, h = 132, 48
    img = Image.new("RGB", (w, h), (248, 249, 252))
    draw = ImageDraw.Draw(img)
    for _ in range(6):
        draw.line(
            [(random.randint(0, w), random.randint(0, h)), (random.randint(0, w), random.randint(0, h))],
            fill=(random.randint(160, 220), random.randint(160, 220), random.randint(180, 230)),
            width=1,
        )
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except OSError:
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 28)
        except OSError:
            font = ImageFont.load_default()
    draw.text((12, 8), text, fill=(25, 40, 90), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def issue_captcha() -> dict:
    """签发验证码，返回给前端的 JSON 字段（含 captcha_type 轮换）。"""
    global _rotate_idx
    with _lock:
        _cleanup_expired_captchas()
        idx = _rotate_idx
        _rotate_idx += 1
    kind = ("image", "math")[idx % 2]
    cid = secrets.token_urlsafe(24)

    if kind == "math":
        a, b = random.randint(2, 12), random.randint(2, 12)
        op = random.choice(["+", "-", "×"])
        if op == "+":
            ans, q = a + b, f"{a} + {b} = ?"
        elif op == "-":
            if a < b:
                a, b = b, a
            ans, q = a - b, f"{a} − {b} = ?"
        else:
            a2, b2 = random.randint(2, 9), random.randint(2, 9)
            ans, q = a2 * b2, f"{a2} × {b2} = ?"
        answer = str(ans)
        payload = {
            "captcha_id": cid,
            "captcha_type": "math",
            "question": q,
        }
    else:
        raw = _random_text_chars(4)
        answer = raw.lower()
        b64 = _render_image_png(raw)
        payload = {
            "captcha_id": cid,
            "captcha_type": "image",
            "image_b64": b64,
        }

    with _lock:
        _store[cid] = {"answer": answer, "kind": kind, "exp": time.monotonic() + CAPTCHA_TTL_SEC}
    return payload


def verify_and_consume(captcha_id: str | None, user_answer: str | None) -> tuple[bool, str]:
    """
    校验并消费验证码（一次性）。
    返回 (ok, error_message)；ok 为 False 时 error_message 供 400 使用。
    """
    cid = (captcha_id or "").strip()
    ua = (user_answer or "").strip()
    if not cid:
        return False, "请输入验证码"
    with _lock:
        _cleanup_expired_captchas()
        row = _store.pop(cid, None)
    if row is None:
        return False, "验证码已失效，请重新获取"
    if time.monotonic() > row["exp"]:
        return False, "验证码已过期，请重新获取"
    expect = row["answer"]
    if row["kind"] == "math":
        try:
            ok = int(ua) == int(expect)
        except ValueError:
            ok = False
    else:
        ok = ua.lower() == expect.lower()
    if not ok:
        return False, "验证码错误"
    return True, ""

