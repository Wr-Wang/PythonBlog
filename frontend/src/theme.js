/**
 * 主题与正文字号（UXR-02 / HUX-01）
 * - theme: system | light | dark，存 localStorage
 * - font: sm | md | lg
 */
const THEME_KEY = "blog_theme";
const FONT_KEY = "blog_font_size";

export function getTheme() {
  try {
    return localStorage.getItem(THEME_KEY) || "system";
  } catch {
    return "system";
  }
}

function effectiveTheme(mode) {
  if (mode === "light") return "light";
  if (mode === "dark") return "dark";
  if (typeof window === "undefined" || !window.matchMedia) return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** 将解析后的亮/暗应用到 document（供 CSS [data-theme] 使用） */
export function applyTheme() {
  const mode = getTheme();
  const eff = effectiveTheme(mode);
  document.documentElement.setAttribute("data-theme", eff);
  document.documentElement.setAttribute("data-theme-pref", mode);
}

export function setTheme(mode) {
  if (mode !== "system" && mode !== "light" && mode !== "dark") return;
  try {
    localStorage.setItem(THEME_KEY, mode);
  } catch {
    /* ignore */
  }
  applyTheme();
}

export function initTheme() {
  applyTheme();
  if (typeof window === "undefined" || !window.matchMedia) return;
  const mql = window.matchMedia("(prefers-color-scheme: dark)");
  mql.addEventListener("change", () => {
    if (getTheme() === "system") applyTheme();
  });
}

export function getFontSize() {
  try {
    return localStorage.getItem(FONT_KEY) || "md";
  } catch {
    return "md";
  }
}

export function setFontSize(size) {
  if (!["sm", "md", "lg"].includes(size)) return;
  try {
    localStorage.setItem(FONT_KEY, size);
  } catch {
    /* ignore */
  }
  document.documentElement.setAttribute("data-font-size", size);
}

export function initFontSize() {
  document.documentElement.setAttribute("data-font-size", getFontSize());
}
