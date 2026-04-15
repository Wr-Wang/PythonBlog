import { nextTick } from "vue";

/** 评论内容可插入的常用表情（Unicode，与系统输入法表情兼容） */
export const COMMENT_EMOJIS = [
  "😀",
  "😃",
  "😄",
  "😁",
  "😅",
  "😂",
  "🤣",
  "😭",
  "😢",
  "😤",
  "😡",
  "🤬",
  "😍",
  "🥰",
  "😘",
  "🤔",
  "👍",
  "👎",
  "👏",
  "🙏",
  "💪",
  "❤️",
  "💯",
  "🔥",
  "✨",
  "🎉",
];

/**
 * @param {string} textareaId
 * @param {import('vue').Ref<string>} textRef
 * @param {string} ch
 */
export function insertEmojiAtCursor(textareaId, textRef, ch) {
  // 优先按光标位置插入；找不到 textarea 时退化为尾部追加。
  const ta = document.getElementById(textareaId);
  if (!ta) {
    textRef.value += ch;
    return;
  }
  const start = typeof ta.selectionStart === "number" ? ta.selectionStart : textRef.value.length;
  const end = typeof ta.selectionEnd === "number" ? ta.selectionEnd : start;
  const before = textRef.value.slice(0, start);
  const after = textRef.value.slice(end);
  textRef.value = before + ch + after;
  nextTick(() => {
    // 下一帧再恢复焦点与光标，避免与 v-model 更新时序冲突。
    ta.focus();
    const pos = start + ch.length;
    try {
      ta.setSelectionRange(pos, pos);
    } catch {
      /* ignore */
    }
  });
}
