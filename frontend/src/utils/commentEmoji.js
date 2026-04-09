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
    ta.focus();
    const pos = start + ch.length;
    try {
      ta.setSelectionRange(pos, pos);
    } catch {
      /* ignore */
    }
  });
}
