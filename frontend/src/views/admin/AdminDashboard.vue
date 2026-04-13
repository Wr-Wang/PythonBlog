<script setup>
import { computed, onMounted, ref } from "vue";
import {
  addBlacklistWord,
  addSearchSynonym,
  addSensitiveWord,
  exportDashboardTrends,
  getDashboardSummary,
  getDashboardTrends,
  getModerationLists,
  getSearchOps,
  listFeatureFlags,
  updateFeatureFlag,
} from "../../api";
import { hasPermission } from "../../utils/permissions";

const loading = ref(false);
const err = ref("");
const data = ref(null);
const trends = ref([]);
const featureFlags = ref([]);
const moderation = ref({ sensitive_words: [], blacklist_words: [] });
const searchOps = ref({ hotwords: [], synonyms: [] });
const newSensitive = ref("");
const newBlacklist = ref("");
const newSynSrc = ref("");
const newSynDst = ref("");
const startDate = ref("");
const endDate = ref("");
const exporting = ref(false);
const canViewDashboard = hasPermission("admin.dashboard.view");
const canExportDashboard = hasPermission("admin.dashboard.export");
const canManageFlags = hasPermission("admin.flags.manage");
const canManageModeration = hasPermission("admin.moderation.manage");
const canManageSearchOps = hasPermission("admin.searchops.manage");

const maxViews = computed(() =>
  Math.max(
    1,
    ...trends.value.map((x) => Number(x.views || 0)),
  ),
);

function defaultDateRange() {
  const now = new Date();
  const end = now.toISOString().slice(0, 10);
  const start = new Date(now.getTime() - 13 * 24 * 3600 * 1000).toISOString().slice(0, 10);
  startDate.value = start;
  endDate.value = end;
}

async function load() {
  loading.value = true;
  err.value = "";
  if (!canViewDashboard) {
    loading.value = false;
    err.value = "缺少权限: admin.dashboard.view";
    return;
  }
  try {
    const [res1, res2] = await Promise.all([
      getDashboardSummary(),
      getDashboardTrends({ start_date: startDate.value, end_date: endDate.value }),
    ]);
    data.value = res1.data;
    trends.value = res2.data.points || [];
    const [f1, f2, f3] = await Promise.all([listFeatureFlags(), getModerationLists(), getSearchOps()]);
    featureFlags.value = f1.data || [];
    moderation.value = f2.data || { sensitive_words: [], blacklist_words: [] };
    searchOps.value = f3.data || { hotwords: [], synonyms: [] };
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

async function toggleFlag(row) {
  await updateFeatureFlag(row.id, {
    enabled: !row.enabled,
    rollout_percent: row.rollout_percent ?? 100,
  });
  await load();
}

async function addSensitive() {
  if (!newSensitive.value.trim()) return;
  await addSensitiveWord(newSensitive.value.trim());
  newSensitive.value = "";
  await load();
}

async function addBlacklist() {
  if (!newBlacklist.value.trim()) return;
  await addBlacklistWord(newBlacklist.value.trim());
  newBlacklist.value = "";
  await load();
}

async function addSyn() {
  if (!newSynSrc.value.trim() || !newSynDst.value.trim()) return;
  await addSearchSynonym(newSynSrc.value.trim(), newSynDst.value.trim());
  newSynSrc.value = "";
  newSynDst.value = "";
  await load();
}

async function onExport(format) {
  exporting.value = true;
  try {
    const res = await exportDashboardTrends(format, {
      start_date: startDate.value,
      end_date: endDate.value,
    });
    const blob = new Blob([res.data], { type: res.headers["content-type"] || "application/octet-stream" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = format === "xlsx" ? "dashboard_trends.xlsx" : "dashboard_trends.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  } finally {
    exporting.value = false;
  }
}

onMounted(() => {
  defaultDateRange();
  load();
});
</script>

<template>
  <section class="card">
    <h2>运营总览</h2>
    <p v-if="loading" class="meta">加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <div v-else-if="data" class="grid">
      <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.5rem">
        <label>开始 <input v-model="startDate" type="date" /></label>
        <label>结束 <input v-model="endDate" type="date" /></label>
        <button type="button" class="secondary" @click="load">刷新趋势</button>
        <button v-if="canExportDashboard" type="button" class="secondary" :disabled="exporting" @click="onExport('csv')">
          导出 CSV
        </button>
        <button v-if="canExportDashboard" type="button" class="secondary" :disabled="exporting" @click="onExport('xlsx')">
          导出 XLSX
        </button>
      </div>
      <p>文章总数：{{ data.posts_total }}</p>
      <p>已发布：{{ data.published_total }}</p>
      <p>待审核：{{ data.pending_total }}</p>
      <p>评论总数：{{ data.comments_total }}</p>
      <p>待审核评论：{{ data.comments_pending }}</p>
      <p>待处理举报：{{ data.reports_pending }}</p>
      <div class="hot-list">
        <h3>热度 TOP10</h3>
        <ol>
          <li v-for="it in data.top_hot_posts || []" :key="it.id">
            {{ it.title }}（{{ it.hot_score }}）
          </li>
        </ol>
      </div>
      <div class="hot-list">
        <h3>浏览趋势（按日）</h3>
        <div v-if="trends.length" class="trend-wrap">
          <div v-for="p in trends" :key="p.date" class="trend-row">
            <span class="trend-date">{{ p.date }}</span>
            <span class="trend-bar"><i :style="{ width: `${(Number(p.views || 0) / maxViews) * 100}%` }" /></span>
            <span class="trend-val">浏览 {{ p.views }} / 点赞 {{ p.likes }} / 收藏 {{ p.favorites }}</span>
          </div>
        </div>
      </div>
      <div class="hot-list">
        <h3>灰度开关</h3>
        <ul>
          <li v-for="f in featureFlags" :key="f.id">
            {{ f.name }}（{{ f.code }}）: {{ f.enabled ? "开启" : "关闭" }}
            <button v-if="canManageFlags" type="button" class="secondary small" @click="toggleFlag(f)">
              切换
            </button>
          </li>
        </ul>
      </div>
      <div class="hot-list">
        <h3>审核策略</h3>
        <p>敏感词：{{ moderation.sensitive_words?.join("、") || "—" }}</p>
        <p>黑名单词：{{ moderation.blacklist_words?.join("、") || "—" }}</p>
        <div v-if="canManageModeration" style="display: flex; gap: 0.5rem; flex-wrap: wrap">
          <input v-model="newSensitive" placeholder="新增敏感词" />
          <button type="button" class="secondary" @click="addSensitive">添加敏感词</button>
          <input v-model="newBlacklist" placeholder="新增黑名单词" />
          <button type="button" class="secondary" @click="addBlacklist">添加黑名单词</button>
        </div>
      </div>
      <div class="hot-list">
        <h3>搜索运营</h3>
        <p>热词：{{ (searchOps.hotwords || []).slice(0, 10).map((x) => `${x.keyword}(${x.cnt})`).join("、") || "—" }}</p>
        <ul>
          <li v-for="s in searchOps.synonyms || []" :key="s.id">{{ s.src }} -> {{ s.dst }}</li>
        </ul>
        <div v-if="canManageSearchOps" style="display: flex; gap: 0.5rem; flex-wrap: wrap">
          <input v-model="newSynSrc" placeholder="同义词原词" />
          <input v-model="newSynDst" placeholder="同义词目标词" />
          <button type="button" class="secondary" @click="addSyn">新增同义词</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.trend-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.trend-row {
  display: grid;
  grid-template-columns: 110px 1fr 200px;
  gap: 0.5rem;
  align-items: center;
}
.trend-date {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}
.trend-bar {
  height: 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
  overflow: hidden;
}
.trend-bar i {
  display: block;
  height: 100%;
  background: var(--accent);
}
.trend-val {
  color: var(--muted);
  font-size: 12px;
}
</style>
