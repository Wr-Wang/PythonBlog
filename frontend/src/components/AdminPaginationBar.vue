<script setup>
import { computed } from "vue";

const props = defineProps({
  total: { type: Number, required: true },
  page: { type: Number, required: true },
  pageSize: { type: Number, required: true },
});

const emit = defineEmits(["update:page", "pageSizeChange"]);

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize) || 1));

function goPrev() {
  if (props.page <= 1) return;
  emit("update:page", props.page - 1);
}

function goNext() {
  if (props.page >= totalPages.value) return;
  emit("update:page", props.page + 1);
}

function goFirst() {
  emit("update:page", 1);
}

function goLast() {
  emit("update:page", totalPages.value);
}

function onSizeChange(e) {
  emit("pageSizeChange", Number(e.target.value));
}
</script>

<template>
  <div
    v-if="total > 0"
    class="admin-pagination"
    role="navigation"
    aria-label="列表分页"
  >
    <label class="admin-page-size">
      每页
      <select :value="pageSize" @change="onSizeChange">
        <option :value="10">10</option>
        <option :value="20">20</option>
        <option :value="50">50</option>
      </select>
      条
    </label>
    <span class="admin-pagination-meta">共 {{ total }} 条 · 第 {{ page }} / {{ totalPages }} 页</span>
    <div class="admin-pagination-btns">
      <button type="button" class="secondary small" :disabled="page <= 1" @click="goFirst">首页</button>
      <button type="button" class="secondary small" :disabled="page <= 1" @click="goPrev">上一页</button>
      <button type="button" class="secondary small" :disabled="page >= totalPages" @click="goNext">
        下一页
      </button>
      <button type="button" class="secondary small" :disabled="page >= totalPages" @click="goLast">
        末页
      </button>
    </div>
  </div>
</template>

<style scoped>
.admin-pagination {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1rem;
  margin-bottom: 0.75rem;
  padding: 0.65rem 0.85rem;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: color-mix(in srgb, var(--surface) 92%, transparent);
  font-size: 0.9rem;
}
.admin-page-size {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.admin-page-size select {
  font: inherit;
  padding: 0.35rem 0.5rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
}
.admin-pagination-meta {
  color: var(--muted);
  flex: 1;
  min-width: 10rem;
}
.admin-pagination-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
</style>
