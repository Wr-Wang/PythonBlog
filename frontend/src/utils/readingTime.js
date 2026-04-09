/**
 * 预估阅读时长（分钟），中文为主按字数约 450 字/分钟（UXR-01）。
 * 富文本 HTML 会先去掉标签再估算。
 */
function plainTextLength(s) {
  if (!s) return 0;
  if (/<[a-z][\s\S]*?>/i.test(s)) {
    return s
      .replace(/<script[\s\S]*?<\/script>/gi, " ")
      .replace(/<style[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;/gi, " ")
      .replace(/\s+/g, " ")
      .trim().length;
  }
  return s.replace(/\s/g, "").length;
}

export function estimateReadingMinutes(text) {
  if (!text || typeof text !== "string") return 1;
  const n = plainTextLength(text);
  return Math.max(1, Math.ceil(n / 450));
}
