<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { getPosts, listFollowedAuthors } from "../api";

const router = useRouter();
const PAGE_SIZE = 15;

const posts = ref([]);
const allLoadedPosts = ref([]);
const loading = ref(true);
const loadingMore = ref(false);
const err = ref("");
const hasMore = ref(true);
const searchQ = ref("");
const activeChannel = ref("recommend");
const followedAuthorIds = ref(readFollowedAuthorIds());

const sentinelRef = ref(null);
let observer = null;

function onSearch(e) {
  /** 顶部搜索框提交：跳转到统一搜索页。 */
  e.preventDefault();
  const q = searchQ.value.trim();
  if (!q) return;
  router.push({ name: "search", query: { q } });
}

function userKey() {
  /** 访客标识：用于关注流与交互行为关联。 */
  const k = "blog_guest_key";
  let v = localStorage.getItem(k);
  if (!v) {
    v = `g_${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(k, v);
  }
  return v;
}

function readFollowedAuthorIds() {
  /** 从本地缓存读取关注作者 ID 列表。 */
  try {
    const raw = localStorage.getItem("blog_followed_author_ids");
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr.map((x) => Number(x)).filter((x) => Number.isFinite(x)) : [];
  } catch {
    return [];
  }
}

async function loadInitial() {
  /** 首次加载：拉关注作者 + 首批文章。 */
  loading.value = true;
  err.value = "";
  posts.value = [];
  hasMore.value = true;
  try {
    try {
      // 优先使用服务端关注列表；失败时回退本地缓存。
      const f = await listFollowedAuthors(userKey());
      const items = Array.isArray(f?.data?.items) ? f.data.items : [];
      followedAuthorIds.value = items.map((x) => Number(x)).filter((x) => Number.isFinite(x));
      localStorage.setItem("blog_followed_author_ids", JSON.stringify(followedAuthorIds.value));
    } catch {
      // ignore and fallback to local cache
    }
    const { data } = await getPosts({
      published_only: true,
      skip: 0,
      limit: 100,
    });
    allLoadedPosts.value = Array.isArray(data) ? data : [];
    applyChannelSlice();
    hasMore.value = posts.value.length >= PAGE_SIZE;
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载失败";
    hasMore.value = false;
  } finally {
    loading.value = false;
  }
}

async function loadMore() {
  /** 无限滚动加载更多文章。 */
  if (!hasMore.value || loadingMore.value || loading.value) return;
  loadingMore.value = true;
  try {
    const { data } = await getPosts({
      published_only: true,
      skip: allLoadedPosts.value.length,
      limit: 60,
    });
    const extra = Array.isArray(data) ? data : [];
    allLoadedPosts.value = [...allLoadedPosts.value, ...extra];
    applyChannelSlice();
    hasMore.value = extra.length >= PAGE_SIZE;
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载更多失败";
    hasMore.value = false;
  } finally {
    loadingMore.value = false;
    await nextTick();
    bindSentinelObserver();
  }
}

const channelTabs = [
  { key: "recommend", label: "推荐" },
  { key: "follow", label: "关注" },
  { key: "hot", label: "热榜" },
  { key: "latest", label: "最新" },
];

function postHotScore(post) {
  /** 统一热度分：用于推荐与热榜排序。 */
  const v = Number(post?.view_count || 0);
  const l = Number(post?.like_count || 0);
  const f = Number(post?.favorite_count || 0);
  const c = Number(post?.comment_count || 0);
  return v + l * 6 + f * 8 + c * 4;
}

function sortByCreatedDesc(a, b) {
  /** 创建时间倒序。 */
  return new Date(b?.created_at || 0).getTime() - new Date(a?.created_at || 0).getTime();
}

function applyChannelSlice() {
  /** 根据频道规则计算展示列表，并维持当前已加载长度窗口。 */
  const all = [...allLoadedPosts.value];
  let list = all;
  if (activeChannel.value === "latest") {
    list = all.sort(sortByCreatedDesc);
  } else if (activeChannel.value === "hot") {
    list = all.sort((a, b) => postHotScore(b) - postHotScore(a));
  } else if (activeChannel.value === "follow") {
    const followed = new Set(followedAuthorIds.value);
    list = all.filter((p) => followed.has(Number(p?.author_id)));
  } else {
    list = all.sort((a, b) => {
      const hotGap = postHotScore(b) - postHotScore(a);
      if (Math.abs(hotGap) > 10) return hotGap;
      return sortByCreatedDesc(a, b);
    });
  }
  posts.value = list.slice(0, Math.max(PAGE_SIZE, posts.value.length || PAGE_SIZE));
}

function switchChannel(key) {
  /** 切换频道并重算列表。 */
  activeChannel.value = key;
  posts.value = [];
  applyChannelSlice();
}

const rightHotTop = computed(() => [...allLoadedPosts.value].sort((a, b) => postHotScore(b) - postHotScore(a)).slice(0, 8));

function bindSentinelObserver() {
  /** 绑定 IntersectionObserver 作为唯一无限加载触发器。 */
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

watch([posts, hasMore, loading], async () => {
  // 列表刷新后重新绑定哨兵监听，避免引用失效。
  if (loading.value) return;
  await nextTick();
  bindSentinelObserver();
});

onMounted(async () => {
  // 首屏加载完成后再绑定 observer，确保 sentinel 已渲染。
  await loadInitial();
  await nextTick();
  bindSentinelObserver();
});

onUnmounted(() => {
  // 组件销毁时断开 observer，避免后台继续触发请求。
  observer?.disconnect();
  observer = null;
});

function formatDate(iso) {
  /** 统一日期文案格式。 */
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("zh-CN");
}
</script>

<template>
  <div class="home-layout">
    <section class="home-main container post-list">
      <form class="home-search" role="search" @submit="onSearch">
        <label class="sr-only" for="home-q">搜索文章</label>
        <input
          id="home-q"
          v-model="searchQ"
          type="search"
          placeholder="搜索标题、摘要或作者…"
          autocomplete="off"
        />
        <button type="submit">搜索</button>
      </form>
      <div class="home-tabs">
        <button
          v-for="tab in channelTabs"
          :key="tab.key"
          type="button"
          class="secondary"
          :class="{ active: activeChannel === tab.key }"
          @click="switchChannel(tab.key)"
        >
          {{ tab.label }}
        </button>
      </div>

      <div v-if="loading" class="home-skeleton" aria-busy="true" aria-label="加载中">
        <div class="skeleton-block" style="height: 2.5rem" />
        <div class="skeleton-line title" />
        <div class="skeleton-line short" />
        <div class="skeleton-line" />
      </div>
      <p v-else-if="err" class="error">{{ err }}</p>
      <template v-else>
        <div v-if="!posts.length" class="empty-state">
          <p class="empty-state-title">当前频道暂时没有内容</p>
          <p>你可以切换频道，或者先关注作者后查看关注流。</p>
        </div>
        <template v-else>
          <article v-for="p in posts" :key="p.id">
            <h2>
              <router-link :to="{ name: 'post', params: { slug: p.slug } }">{{ p.title }}</router-link>
            </h2>
            <p v-if="p.excerpt" class="meta">{{ p.excerpt }}</p>
            <p class="meta">{{ formatDate(p.created_at) }} · 热度 {{ postHotScore(p) }}</p>
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
    </section>

    <aside class="home-right card">
      <h3>热榜 Top 8</h3>
      <ol class="home-hot-rank">
        <li v-for="item in rightHotTop" :key="item.id">
          <router-link :to="{ name: 'post', params: { slug: item.slug } }">{{ item.title }}</router-link>
        </li>
      </ol>
    </aside>
  </div>
</template>

<style scoped>
.home-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 1rem;
  max-width: 1280px;
  margin: 0 auto;
}
.home-main {
  max-width: none;
}
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
}
.home-search button {
  padding: 0.5rem 0.85rem;
}
.home-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.home-tabs button.active {
  border-color: var(--accent);
  color: var(--accent-hover);
}
.home-right {
  align-self: start;
  position: sticky;
  top: 1rem;
}
.home-hot-rank {
  margin: 0;
  padding-left: 1.1rem;
  display: grid;
  gap: 0.4rem;
}
.home-hot-rank a {
  color: var(--text);
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
@media (max-width: 1180px) {
  .home-layout {
    grid-template-columns: 1fr;
  }
  .home-right {
    position: static;
  }
}
</style>
