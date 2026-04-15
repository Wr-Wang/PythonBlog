<script setup>
import { onMounted, ref } from "vue";
import { listPublicColumns } from "../api";

const loading = ref(true);
const err = ref("");
const items = ref([]);

onMounted(async () => {
  /** 专栏页初始化：加载公开专栏列表。 */
  loading.value = true;
  err.value = "";
  try {
    const { data } = await listPublicColumns({ skip: 0, limit: 60 });
    items.value = data?.items || [];
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "专栏加载失败";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="container">
    <h2>专栏</h2>
    <p class="meta">按主题沉淀的系列内容。</p>
    <p v-if="loading" class="meta">加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <div v-else class="columns-grid">
      <article v-for="c in items" :key="c.id" class="column-card">
        <h3>
          <router-link :to="{ name: 'column-detail', params: { slug: c.slug } }">{{ c.name }}</router-link>
        </h3>
        <p v-if="c.description" class="meta">{{ c.description }}</p>
        <p class="meta">文章数 {{ c.visible_post_count ?? (c.post_ids || []).length }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.columns-grid {
  margin-top: 0.8rem;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 0.8rem;
}
.column-card {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0.75rem 0.85rem;
  background: var(--surface);
}
.column-card h3 {
  margin: 0 0 0.35rem;
  font-size: 1.05rem;
}
</style>
