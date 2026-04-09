<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { getPosts } from "../api";

const router = useRouter();
const PAGE_SIZE = 15;

const posts = ref([]);
const loading = ref(true);
const loadingMore = ref(false);
const err = ref("");
const hasMore = ref(true);
const searchQ = ref("");

const sentinelRef = ref(null);
let observer = null;

function onSearch(e) {
  e.preventDefault();
  const q = searchQ.value.trim();
  if (!q) return;
  router.push({ name: "search", query: { q } });
}

async function loadInitial() {
  loading.value = true;
  err.value = "";
  posts.value = [];
  hasMore.value = true;
  try {
    const { data } = await getPosts({
      published_only: true,
      skip: 0,
      limit: PAGE_SIZE,
    });
    posts.value = data;
    hasMore.value = data.length >= PAGE_SIZE;
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载失败";
    hasMore.value = false;
  } finally {
    loading.value = false;
  }
}

async function loadMore() {
  if (!hasMore.value || loadingMore.value || loading.value) return;
  loadingMore.value = true;
  try {
    const { data } = await getPosts({
      published_only: true,
      skip: posts.value.length,
      limit: PAGE_SIZE,
    });
    posts.value = [...posts.value, ...data];
    hasMore.value = data.length >= PAGE_SIZE;
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载更多失败";
    hasMore.value = false;
  } finally {
    loadingMore.value = false;
    await nextTick();
    bindSentinelObserver();
  }
}

function bindSentinelObserver() {
  observer?.disconnect();
  observer = null;
  const el = sentinelRef.value;
  if (!el || !hasMore.value) return;
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) loadMore();
    },
    { root: null, rootMargin: "240px 0px", threshold: 0 },
  );
  observer.observe(el);
}

function onWindowScroll() {
  if (!hasMore.value || loadingMore.value || loading.value) return;
  const el = document.documentElement;
  const nearBottom = el.scrollHeight - window.scrollY - window.innerHeight < 400;
  if (nearBottom) loadMore();
}

watch([posts, hasMore, loading], async () => {
  if (loading.value) return;
  await nextTick();
  bindSentinelObserver();
});

onMounted(async () => {
  await loadInitial();
  await nextTick();
  bindSentinelObserver();
  window.addEventListener("scroll", onWindowScroll, { passive: true });
});

onUnmounted(() => {
  window.removeEventListener("scroll", onWindowScroll);
  observer?.disconnect();
  observer = null;
});

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("zh-CN");
}
</script>

<template>
  <div class="container post-list">
    <form class="home-search" role="search" @submit="onSearch">
      <label class="sr-only" for="home-q">搜索文章</label>
      <input
        id="home-q"
        v-model="searchQ"
        type="search"
        placeholder="搜索标题或摘要…"
        autocomplete="off"
      />
      <button type="submit">搜索</button>
    </form>
    <div v-if="loading" class="home-skeleton" aria-busy="true" aria-label="加载中">
      <div class="skeleton-block" style="height: 2.5rem" />
      <div class="skeleton-line title" />
      <div class="skeleton-line short" />
      <div class="skeleton-line" />
      <div class="skeleton-line title" />
      <div class="skeleton-line short" />
    </div>
    <p v-else-if="err" class="error">{{ err }}</p>
    <template v-else>
      <div v-if="!posts.length" class="empty-state">
        <p class="empty-state-title">还没有公开文章</p>
        <p>作者发布文章后，会在这里列出。你也可以用上方搜索框查找内容。</p>
      </div>
      <template v-else>
        <article v-for="p in posts" :key="p.id">
          <h2>
            <router-link :to="{ name: 'post', params: { slug: p.slug } }">{{ p.title }}</router-link>
          </h2>
          <p v-if="p.excerpt" class="meta">{{ p.excerpt }}</p>
          <p class="meta">{{ formatDate(p.created_at) }}</p>
        </article>
        <div
          v-if="hasMore"
          ref="sentinelRef"
          class="home-scroll-sentinel"
          aria-hidden="true"
        />
        <p v-if="loadingMore" class="home-load-hint" aria-live="polite">正在加载更多…</p>
        <p v-else-if="!hasMore" class="home-load-hint muted">已加载全部文章</p>
      </template>
    </template>
  </div>
</template>

<style scoped>
.home-search {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 1.25rem;
  align-items: center;
}
.home-search input {
  flex: 1;
  min-width: 12rem;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font: inherit;
}
.home-search button {
  padding: 0.5rem 0.85rem;
}
.home-scroll-sentinel {
  height: 1px;
  margin: 0;
  padding: 0;
  pointer-events: none;
  visibility: hidden;
}
.home-load-hint {
  text-align: center;
  font-size: 0.9rem;
  color: var(--muted);
  margin: 1rem 0 0.5rem;
}
.home-load-hint.muted {
  opacity: 0.85;
}
</style>
