<script setup>
import { onMounted, ref } from "vue";
import { getPosts } from "../api";

const loading = ref(true);
const err = ref("");
const items = ref([]);

onMounted(async () => {
  loading.value = true;
  err.value = "";
  try {
    const { data } = await getPosts({ published_only: true, sort: "hot", skip: 0, limit: 50 });
    items.value = Array.isArray(data) ? data : [];
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "热榜加载失败";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="container hot-page">
    <h2>全站热榜</h2>
    <p class="meta">按综合热度排序（浏览 + 点赞 + 收藏）。</p>
    <p v-if="loading" class="meta">加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <ol v-else class="hot-list">
      <li v-for="(item, idx) in items" :key="item.id" class="hot-item">
        <span class="rank">{{ idx + 1 }}</span>
        <div class="hot-main">
          <router-link :to="{ name: 'post', params: { slug: item.slug } }">{{ item.title }}</router-link>
          <p class="meta">浏览 {{ item.view_count || 0 }} · 点赞 {{ item.like_count || 0 }} · 收藏 {{ item.favorite_count || 0 }}</p>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.hot-list {
  margin: 1rem 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.6rem;
}
.hot-item {
  display: grid;
  grid-template-columns: 2rem 1fr;
  gap: 0.6rem;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.65rem 0.8rem;
}
.rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 50%;
  background: rgba(91, 155, 213, 0.18);
  color: var(--accent-hover);
  font-weight: 700;
}
</style>
