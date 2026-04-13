<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { getDashboardSummary } from "../../api";

const router = useRouter();
const loading = ref(true);
const err = ref("");
const summary = ref({
  posts_total: 0,
  published_total: 0,
  pending_total: 0,
  comments_total: 0,
  comments_pending: 0,
  reports_pending: 0,
});

const quick = [
  { title: "内容创作", desc: "新建与维护文章", to: "/admin/posts" },
  { title: "流程审核", desc: "快速处理待审内容", to: "/admin/workflow" },
  { title: "权限配置", desc: "角色与菜单授权", to: "/admin/permissions" },
  { title: "运营分析", desc: "趋势与导出能力", to: "/admin/dashboard" },
];

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const { data } = await getDashboardSummary();
    summary.value = { ...summary.value, ...(data || {}) };
  } catch (e) {
    // 首页不阻断访问，失败时给温和提示。
    err.value = e.response?.data?.detail || e.message || "概览数据加载失败";
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="admin-home">
    <div class="hero card">
      <div>
        <p class="meta">Welcome Back</p>
        <h2>后台工作台</h2>
        <p class="subtitle">集中处理内容、流程、权限与运营，提升日常管理效率。</p>
      </div>
    </div>

    <div class="metrics card">
      <p v-if="loading" class="meta">加载中…</p>
      <p v-else-if="err" class="error">{{ err }}</p>
      <div v-else class="metric-grid">
        <article class="metric">
          <span class="metric-label">文章总数</span>
          <strong>{{ summary.posts_total }}</strong>
        </article>
        <article class="metric">
          <span class="metric-label">已发布</span>
          <strong>{{ summary.published_total }}</strong>
        </article>
        <article class="metric">
          <span class="metric-label">待审核</span>
          <strong>{{ summary.pending_total }}</strong>
        </article>
        <article class="metric">
          <span class="metric-label">待审评论</span>
          <strong>{{ summary.comments_pending }}</strong>
        </article>
      </div>
    </div>

    <div class="quick-grid">
      <article v-for="x in quick" :key="x.to" class="quick card">
        <h3>{{ x.title }}</h3>
        <p class="meta">{{ x.desc }}</p>
        <a href="#" class="jump" @click.prevent="router.push(x.to)">立即进入</a>
      </article>
    </div>
  </section>
</template>

<style scoped>
.admin-home {
  display: grid;
  gap: 0.8rem;
}
.hero h2 {
  margin: 0.15rem 0 0.3rem;
  font-size: 1.35rem;
}
.subtitle {
  margin: 0;
  color: var(--muted);
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.6rem;
}
.metric {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.55rem 0.7rem;
  background: color-mix(in srgb, var(--surface) 94%, transparent);
}
.metric-label {
  display: block;
  color: var(--muted);
}
.metric strong {
  font-size: 1.2rem;
}
.quick-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.7rem;
}
.quick h3 {
  margin: 0 0 0.25rem;
}
.jump {
  display: inline-block;
  margin-top: 0.35rem;
}
</style>
