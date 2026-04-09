<script setup>
import { onMounted, ref } from "vue";
import { getPosts } from "../api";

const posts = ref([]);
const loading = ref(true);
const err = ref("");

onMounted(async () => {
  try {
    const { data } = await getPosts({ published_only: true });
    posts.value = data;
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载失败";
  } finally {
    loading.value = false;
  }
});

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("zh-CN");
}
</script>

<template>
  <div class="container post-list">
    <p v-if="loading">加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <template v-else>
      <p v-if="!posts.length" class="meta">暂无公开文章。</p>
      <article v-for="p in posts" :key="p.id">
        <h2>
          <router-link :to="{ name: 'post', params: { slug: p.slug } }">{{ p.title }}</router-link>
        </h2>
        <p v-if="p.excerpt" class="meta">{{ p.excerpt }}</p>
        <p class="meta">{{ formatDate(p.created_at) }}</p>
      </article>
    </template>
  </div>
</template>
