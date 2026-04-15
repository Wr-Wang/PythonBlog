<script setup>
import { onMounted, ref } from "vue";
import { getRecommendPosts, listPublicColumns } from "../api";

const loading = ref(true);
const err = ref("");
const items = ref([]);
const columns = ref([]);

const topicCards = [
  { name: "Python 开发", desc: "后端实践、性能优化与工程经验" },
  { name: "前端工程化", desc: "Vue、组件设计与页面体验" },
  { name: "系统部署", desc: "IIS、数据库、发布与稳定性" },
];

onMounted(async () => {
  /** 发现页初始化：并行拉推荐文章与推荐专栏。 */
  loading.value = true;
  err.value = "";
  try {
    const { data } = await getRecommendPosts(24);
    items.value = Array.isArray(data) ? data : [];
    const c = await listPublicColumns({ skip: 0, limit: 6 });
    columns.value = c?.data?.items || [];
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "发现页加载失败";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="container discover-page">
    <h2>发现</h2>
    <p class="meta">精选内容、话题方向与推荐阅读。</p>
    <div class="discover-grid">
      <div class="discover-main">
        <p v-if="loading" class="meta">加载中…</p>
        <p v-else-if="err" class="error">{{ err }}</p>
        <article v-for="p in items" v-else :key="p.id" class="discover-item">
          <h3><router-link :to="{ name: 'post', params: { slug: p.slug } }">{{ p.title }}</router-link></h3>
          <p v-if="p.excerpt" class="meta">{{ p.excerpt }}</p>
        </article>
      </div>
      <aside class="discover-side card">
        <h3>推荐话题</h3>
        <ul>
          <li v-for="topic in topicCards" :key="topic.name">
            <strong>{{ topic.name }}</strong>
            <p class="meta">{{ topic.desc }}</p>
          </li>
        </ul>
        <h3 style="margin-top: 0.8rem">推荐专栏</h3>
        <ul>
          <li v-for="c in columns" :key="c.id">
            <router-link :to="{ name: 'column-detail', params: { slug: c.slug } }">{{ c.name }}</router-link>
          </li>
        </ul>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.discover-grid {
  margin-top: 0.9rem;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 1rem;
}
.discover-item {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.7rem 0.8rem;
  margin-bottom: 0.55rem;
}
.discover-item h3 {
  margin: 0 0 0.35rem;
  font-size: 1.05rem;
}
.discover-side ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.65rem;
}
.discover-side strong {
  font-size: 0.95rem;
}
@media (max-width: 1100px) {
  .discover-grid {
    grid-template-columns: 1fr;
  }
}
</style>
