<script setup>
import { computed, onMounted, watch, ref } from "vue";
import { useRoute } from "vue-router";
import { getPublicColumnBySlug } from "../api";

const route = useRoute();
const slug = computed(() => String(route.params.slug || ""));
const loading = ref(true);
const err = ref("");
const column = ref(null);

async function load() {
  /** 按 slug 加载专栏详情。 */
  if (!slug.value) return;
  loading.value = true;
  err.value = "";
  try {
    const { data } = await getPublicColumnBySlug(slug.value);
    column.value = data || null;
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "专栏加载失败";
    column.value = null;
  } finally {
    loading.value = false;
  }
}

const visiblePosts = computed(() => {
  /** 仅输出后端已筛选的可见文章数组。 */
  const p = column.value?.posts;
  return Array.isArray(p) ? p : [];
});

onMounted(load);
// 路由参数变化时刷新详情（同组件复用场景）。
watch(slug, load);
</script>

<template>
  <section class="container">
    <p v-if="loading" class="meta">加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <template v-else-if="column">
      <h2>{{ column.name }}</h2>
      <p v-if="column.description" class="meta">{{ column.description }}</p>
      <p class="meta">共 {{ visiblePosts.length }} 篇已发布文章</p>
      <div v-if="!visiblePosts.length" class="empty-hint">该专栏暂无对访客可见的文章。</div>
      <div v-else class="column-posts">
        <article v-for="p in visiblePosts" :key="p.id" class="column-post-item">
          <h3 class="post-title">
            <router-link :to="{ name: 'post', params: { slug: p.slug } }">{{ p.title }}</router-link>
          </h3>
          <p class="meta line">
            <span v-if="p.author_name">{{ p.author_name }}</span>
            <span v-if="p.published_at">{{ p.author_name ? " · " : "" }}{{ p.published_at }}</span>
          </p>
        </article>
      </div>
    </template>
  </section>
</template>

<style scoped>
.column-posts {
  margin-top: 0.8rem;
  display: grid;
  gap: 0.5rem;
}
.column-post-item {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.6rem 0.75rem;
}
.post-title {
  margin: 0 0 0.25rem;
  font-size: 1.05rem;
}
.post-title a {
  color: var(--text);
  text-decoration: none;
}
.post-title a:hover {
  color: var(--accent);
  text-decoration: underline;
}
.line {
  margin: 0;
}
.empty-hint {
  margin-top: 0.75rem;
  color: var(--muted);
  font-size: 0.95rem;
}
</style>
