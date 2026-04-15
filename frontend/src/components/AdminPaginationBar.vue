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
    <div class="admin-pagination-main">
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
    </div>
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
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem 1rem;
  margin-bottom: 0.75rem;
  padding: 0.65rem 0.85rem;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: color-mix(in srgb, var(--surface) 92%, transparent);
  font-size: 12px;
  width: 100%;
  min-width: 0;
}
.admin-pagination-main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.9rem;
  min-width: 0;
  flex: 1 1 auto;
}
.admin-page-size {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  min-width: 0;
}
.admin-page-size select {
  font: inherit;
  width: auto;
  min-width: 4.5rem;
  max-width: 8rem;
  min-height: 30px;
  height: 30px;
  padding: 0.2rem 2rem 0.2rem 0.45rem;
  font-size: 12px;
}
.admin-pagination-meta {
  color: var(--muted);
  flex: 1 1 12rem;
  min-width: 0;
  text-align: left;
}
.admin-pagination-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  justify-content: flex-end;
  min-width: 0;
  margin-left: auto;
}

@media (max-width: 768px) {
  .admin-pagination {
    flex-direction: column;
    align-items: stretch;
    padding: 0.55rem 0.65rem;
  }
  .admin-pagination-main,
  .admin-pagination-btns {
    width: 100%;
  }
}

@media (max-width: 1400px) and (max-height: 800px) {
  .admin-pagination {
    margin-bottom: 0.5rem;
    padding: 0.45rem 0.6rem;
    gap: 0.45rem 0.6rem;
  }
  .admin-page-size select {
    height: 26px;
    min-height: 26px;
    padding: 0.12rem 1.75rem 0.12rem 0.35rem;
  }
  .admin-pagination-btns button {
    height: 28px;
    padding: 0.2rem 0.55rem;
  }
}
</style>
