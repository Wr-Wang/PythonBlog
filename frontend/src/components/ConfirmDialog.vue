<script setup>
import BaseModal from "./BaseModal.vue";

defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: "确认" },
  message: { type: String, default: "" },
});
const emit = defineEmits(["close", "confirm"]);
</script>

<template>
  <BaseModal :open="open" :title="title" @close="emit('close')">
    <p style="margin: 0 0 1rem; color: var(--muted)">{{ message }}</p>
    <template #footer>
      <button type="button" class="secondary" @click="emit('close')">取消</button>
      <button type="button" class="danger" @click="emit('confirm')">确定删除</button>
    </template>
  </BaseModal>
</template>
