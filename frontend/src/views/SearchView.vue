<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { searchPosts } from "../api";

const route = useRoute();
const q = computed(() => String(route.query.q || "").trim());

const posts = ref([]);
const loading = ref(true);
const err = ref("");

async function load() {
  if (!q.value) {
    posts.value = [];
    loading.value = false;
    err.value = "";
    return;
  }
  loading.value = true;
  err.value = "";
  try {
    const { data } = await searchPosts({ q: q.value, limit: 50 });
    posts.value = data;
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "搜索失败";
  } finally {
    loading.value = false;
  }
}

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("zh-CN");
}

onMounted(load);
watch(q, load);
</script>

<template>
  <div class="container post-list">
    <p class="meta search-meta">
      <template v-if="q">
        关键词「<strong>{{ q }}</strong>」的搜索结果
      </template>
      <template v-else>请输入关键词</template>
      ·
      <router-link to="/">返回首页</router-link>
    </p>
    <div
      v-if="loading && q"
      class="search-skeleton"
      aria-busy="true"
      aria-label="搜索中"
    >
      <div class="skeleton-line title" />
      <div class="skeleton-line" />
      <div class="skeleton-line short" />
      <div class="skeleton-line title" />
      <div class="skeleton-line short" />
    </div>
    <p v-else-if="loading" class="meta">加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <template v-else-if="q">
      <div v-if="!posts.length" class="empty-state">
        <p class="empty-state-title">没有找到匹配文章</p>
        <p>试试换个关键词，或返回首页浏览全部文章。</p>
      </div>
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

<style scoped>
.search-meta {
  margin-bottom: 1rem;
}
</style>
