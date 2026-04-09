<script setup>
defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: "" },
  wide: { type: Boolean, default: false },
});
const emit = defineEmits(["close"]);
function onBackdrop() {
  emit("close");
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-mask" @click.self="onBackdrop">
      <div class="modal-panel" :class="{ wide }" role="dialog" aria-modal="true">
        <div class="modal-head">
          <h2 class="modal-title">{{ title }}</h2>
          <button type="button" class="icon-close secondary" aria-label="关闭" @click="emit('close')">×</button>
        </div>
        <div class="modal-body">
          <slot />
        </div>
        <div v-if="$slots.footer" class="modal-foot">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 2rem 1rem;
  overflow: auto;
}
.modal-panel {
  width: 100%;
  max-width: 480px;
  min-width: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4);
}
.modal-panel.wide {
  max-width: min(920px, calc(100vw - 2rem));
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border);
}
.modal-title {
  margin: 0;
  font-size: 1.1rem;
}
.icon-close {
  font-size: 1.5rem;
  line-height: 1;
  padding: 0.15rem 0.5rem;
}
.modal-body {
  padding: 1.25rem;
  max-height: 70vh;
  overflow: auto;
  min-width: 0;
}
/* 宽弹窗：不在此层裁剪，避免 Quill 等富文本工具栏下拉被截断；整体由 .modal-mask 滚动 */
.modal-panel.wide .modal-body {
  max-height: none;
  overflow: visible;
}
.modal-foot {
  padding: 0 1.25rem 1.25rem;
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  flex-wrap: wrap;
}
</style>
