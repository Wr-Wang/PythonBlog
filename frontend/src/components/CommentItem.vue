<script setup>
import { computed, ref } from "vue";
import CommentItem from "./CommentItem.vue";

const props = defineProps({
  node: { type: Object, required: true },
  defaultRepliesCollapsed: { type: Boolean, default: true },
});
const emit = defineEmits(["reply"]);
const textExpanded = ref(false);
const repliesExpanded = ref(!props.defaultRepliesCollapsed);

const hasChildren = computed(() => Array.isArray(props.node.children) && props.node.children.length > 0);
const shouldFoldText = computed(() => {
  const s = String(props.node.content || "");
  return s.length > 70 || s.includes("\n");
});

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("zh-CN");
}
</script>

<template>
  <li class="c-item">
    <div class="c-head">
      <strong>{{ node.author_name }}</strong>
      <span class="meta">{{ formatDate(node.created_at) }}</span>
      <button
        type="button"
        class="secondary small reply-btn"
        title="回复这条评论"
        @click="emit('reply', node)"
      >
        回复
      </button>
    </div>
    <p class="c-body" :class="{ 'c-body-fold': shouldFoldText && !textExpanded }">{{ node.content }}</p>
    <button v-if="shouldFoldText" type="button" class="c-link-btn" @click="textExpanded = !textExpanded">
      {{ textExpanded ? "收起" : "展开" }}
    </button>

    <button v-if="hasChildren && !repliesExpanded" type="button" class="c-link-btn" @click="repliesExpanded = true">
      展开 {{ node.children.length }} 条回复
    </button>
    <template v-if="hasChildren && repliesExpanded">
      <ul class="nested">
        <CommentItem
          v-for="ch in node.children"
          :key="ch.id"
          :node="ch"
          :default-replies-collapsed="true"
          @reply="emit('reply', $event)"
        />
      </ul>
      <button type="button" class="c-link-btn" @click="repliesExpanded = false">收起回复</button>
    </template>
  </li>
</template>

<style scoped>
.c-item {
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border);
}
.nested {
  list-style: none;
  margin: 0.5rem 0 0;
  padding: 0 0 0 0.75rem;
  border-left: 2px solid var(--border);
}
.c-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
  margin-bottom: 0.35rem;
}
.c-body {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: normal;
  line-height: 1.55;
  font-family: var(--font-sans, "Segoe UI", system-ui, sans-serif, "Segoe UI Emoji", "Apple Color Emoji",
    "Noto Color Emoji", emoji);
}
.c-body-fold {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.small {
  padding: 0.2rem 0.5rem;
  font-size: 0.8rem;
}
.reply-btn {
  margin-left: auto;
}
.c-link-btn {
  margin-top: 0.3rem;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--primary);
  cursor: pointer;
  font-size: 0.875rem;
}
</style>
