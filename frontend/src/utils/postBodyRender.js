/**
 * 文章正文：富文本 HTML 与旧版 Markdown 兼容展示。
 */
import DOMPurify from "dompurify";
import { marked } from "marked";

const LOOKS_LIKE_HTML = /^\s*<[!/?]?[a-zA-Z]/;

function iframeSrcAllowed(src) {
  if (!src || typeof src !== "string") return false;
  const s = src.trim();
  const low = s.toLowerCase();
  if (low.startsWith("javascript:") || low.startsWith("data:") || low.startsWith("vbscript:")) {
    return false;
  }
  let u = s;
  if (u.startsWith("//")) u = "https:" + u;
  try {
    const url = new URL(u, typeof window !== "undefined" ? window.location.origin : "http://localhost");
    if (url.protocol !== "http:" && url.protocol !== "https:") return false;
    const h = (url.hostname || "").toLowerCase().replace(/^www\./, "");
    const exact = new Set(["player.bilibili.com", "player.vimeo.com"]);
    if (exact.has(h)) return true;
    const suf = [
      "youtube.com",
      "youtube-nocookie.com",
      "youtu.be",
      "bilibili.com",
      "vimeo.com",
    ];
    return suf.some((x) => h === x || h.endsWith("." + x));
  } catch {
    return false;
  }
}

let purifyHooks = false;

function ensurePurifyHooks() {
  if (purifyHooks) return;
  purifyHooks = true;
  DOMPurify.addHook("uponSanitizeAttribute", (node, data) => {
    if (data.attrName === "src" && node && node.tagName === "IFRAME") {
      if (!iframeSrcAllowed(String(data.attrValue || ""))) {
        data.keepAttr = false;
      }
    }
  });
}

export function postBodyLooksLikeHtml(raw) {
  return LOOKS_LIKE_HTML.test(raw || "");
}

/**
 * 返回可安全 v-html 的 HTML；Markdown 则先转为 HTML 再净化。
 */
export function sanitizePostBodyHtml(raw) {
  if (!raw) return "";
  ensurePurifyHooks();
  let html = raw;
  if (!postBodyLooksLikeHtml(raw)) {
    html = marked.parse(raw, { async: false });
  }
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    ADD_TAGS: ["iframe"],
    ADD_ATTR: ["allow", "allowfullscreen", "frameborder", "scrolling", "target", "rel"],
  });
}
