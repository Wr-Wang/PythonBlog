<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import Quill from "quill";
import "quill/dist/quill.snow.css";
import { uploadImage } from "../api";
import { COMMENT_EMOJIS } from "../utils/commentEmoji";

const props = defineProps({
  modelValue: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue"]);

const host = ref(null);
let quill = null;
const syncing = ref(false);

function buildToolbarHandlers() {
  return {
    image: function imageHandler() {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "image/jpeg,image/png,image/gif,image/webp";
      input.onchange = async () => {
        const file = input.files?.[0];
        if (!file || !quill) return;
        try {
          const { data } = await uploadImage(file);
          const url = data.url;
          const range = quill.getSelection(true);
          const idx = range ? range.index : quill.getLength();
          quill.insertEmbed(idx, "image", url, "user");
          quill.setSelection(idx + 1, 0, "silent");
        } catch {
          /* 由上层表单或 axios 拦截器提示 */
        }
      };
      input.click();
    },
  };
}

onMounted(() => {
  if (!host.value) return;
  quill = new Quill(host.value, {
    theme: "snow",
    placeholder: "支持文字、图片、视频嵌入与表情…",
    modules: {
      toolbar: {
        container: [
          [{ header: [1, 2, 3, false] }],
          ["bold", "italic", "underline", "strike"],
          ["blockquote", "code-block"],
          [{ list: "ordered" }, { list: "bullet" }],
          ["link", "image", "video"],
          ["clean"],
        ],
        handlers: buildToolbarHandlers(),
      },
    },
  });

  const initial = props.modelValue || "";
  if (initial.trim()) {
    syncing.value = true;
    quill.clipboard.dangerouslyPasteHTML(initial);
    syncing.value = false;
  }

  quill.on("text-change", () => {
    if (syncing.value || !quill) return;
    emit("update:modelValue", quill.root.innerHTML);
  });
});

onBeforeUnmount(() => {
  quill = null;
});

watch(
  () => props.modelValue,
  (v) => {
    if (!quill) return;
    const html = quill.root.innerHTML;
    const next = v || "";
    if (next === html) return;
    syncing.value = true;
    quill.clipboard.dangerouslyPasteHTML(next);
    syncing.value = false;
  },
);

function insertEmoji(ch) {
  if (!quill) return;
  const range = quill.getSelection(true);
  const idx = range ? range.index : quill.getLength();
  quill.insertText(idx, ch, "user");
  quill.setSelection(idx + ch.length, 0, "silent");
}
</script>

<template>
  <div class="rte-wrap">
    <div class="rte-emoji-bar" role="toolbar" aria-label="插入表情">
      <button
        v-for="(em, i) in COMMENT_EMOJIS"
        :key="i"
        type="button"
        class="rte-emoji-btn"
        :title="'插入 ' + em"
        @click="insertEmoji(em)"
      >
        {{ em }}
      </button>
    </div>
    <!-- Quill 会在本节点前插入 .ql-toolbar，并给本节点加上 ql-container ql-snow（与 rte-quill-host 同一元素） -->
    <div ref="host" class="rte-quill-host" aria-label="富文本正文" />
  </div>
</template>

<style scoped>
/*
 * Quill Snow 实际 DOM（初始化后）：
 * .rte-wrap
 *   .rte-emoji-bar
 *   .ql-toolbar.ql-snow          ← 插在 host 之前，是 wrap 的直接子节点（不是 host 的子节点）
 *   .rte-quill-host.ql-container.ql-snow
 *     .ql-editor …
 * 因此工具栏样式必须挂在 .rte-wrap 下，不能写 .rte-quill-host :deep(.ql-toolbar)。
 */
.rte-wrap {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  position: relative;
  z-index: 0;
  gap: 0;
}

.rte-emoji-bar {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.35rem;
  margin-bottom: 0.45rem;
  padding: 0.45rem 0.5rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--emoji-bar-bg);
  font-family: var(
    --font-sans,
    "Segoe UI",
    system-ui,
    sans-serif,
    "Segoe UI Emoji",
    "Apple Color Emoji",
    "Noto Color Emoji",
    emoji
  );
}

.rte-emoji-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2rem;
  min-height: 2rem;
  padding: 0.1rem 0.25rem;
  font-size: 1.2rem;
  line-height: 1;
  font-weight: 400;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text);
  cursor: pointer;
}
.rte-emoji-btn:hover {
  background: color-mix(in srgb, var(--text) 8%, transparent);
  border-color: var(--border);
}

/* 工具栏：Quill 插入的兄弟节点 */
.rte-wrap :deep(.ql-toolbar.ql-snow) {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px 4px;
  row-gap: 6px;
  padding: 8px;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  border: 1px solid var(--border);
  border-bottom: none;
  background: color-mix(in srgb, var(--surface) 92%, var(--bg));
  box-sizing: border-box;
  max-width: 100%;
  position: relative;
  z-index: 2;
}

.rte-wrap :deep(.ql-snow .ql-formats) {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  margin-right: 6px;
}

.rte-wrap :deep(.ql-toolbar .ql-picker-options) {
  z-index: 2500;
  background: var(--surface);
  border-color: var(--border);
}

.rte-wrap :deep(.ql-tooltip) {
  z-index: 2600;
}

/* host 即 .ql-container：参与文档流，禁止 height:100% 叠在下方表单上 */
.rte-quill-host {
  flex-shrink: 0;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  font-family: var(--font-sans);
  font-size: 0.95rem;
  height: auto !important;
  min-height: 200px;
  border: 1px solid var(--border);
  border-top: none;
  border-bottom-left-radius: 8px;
  border-bottom-right-radius: 8px;
  background: var(--surface);
  color: var(--text);
  position: relative;
  z-index: 1;
}

.rte-quill-host :deep(.ql-editor) {
  height: auto !important;
  min-height: 180px;
  max-height: min(380px, 42vh);
  overflow-x: hidden;
  overflow-y: auto;
  word-break: break-word;
}

.rte-wrap :deep(.ql-stroke) {
  stroke: var(--muted);
}
.rte-wrap :deep(.ql-fill) {
  fill: var(--muted);
}
.rte-wrap :deep(.ql-picker-label) {
  color: var(--text);
}

.rte-quill-host :deep(.ql-editor.ql-blank::before) {
  color: var(--muted);
  font-style: normal;
  left: 15px;
  right: 15px;
}
</style>
