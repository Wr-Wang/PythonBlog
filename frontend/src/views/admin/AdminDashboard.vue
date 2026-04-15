<script setup>
import { computed, onMounted, ref } from "vue";
import {
  addBlacklistWord,
  addSearchSynonym,
  addSensitiveWord,
  exportDashboardTrends,
  getDashboardTrends,
  getDashboardVisual,
  getModerationLists,
  getSearchOps,
  listFeatureFlags,
  listSensitiveGroups,
  toggleSensitiveGroup,
  updateFeatureFlag,
} from "../../api";
import { hasPermission } from "../../utils/permissions";

const loading = ref(false);
const err = ref("");
const visual = ref(null);
const trends = ref([]);
const featureFlags = ref([]);
const moderation = ref({ sensitive_words: [], blacklist_words: [] });
const sensitiveGroups = ref([]);
const searchOps = ref({ hotwords: [], synonyms: [] });
const newSensitive = ref("");
const newBlacklist = ref("");
const newSynSrc = ref("");
const newSynDst = ref("");
const startDate = ref("");
const endDate = ref("");
const categoryId = ref("");
const authorId = ref("");
const reviewStatus = ref("all");
const activeTab = ref("overview");
const exporting = ref(false);
const trendMode = ref("split"); // split | combined
const trendGroupBy = ref("day"); // day | week | month
const combinedChartType = ref("line"); // line | bar | stack
const moduleChartType = ref({
  views: "line",
  likes: "bar",
  comments: "line",
  published_posts: "bar",
});
const canViewDashboard = hasPermission("admin.dashboard.view");
const canExportDashboard = hasPermission("admin.dashboard.export");
const canManageFlags = hasPermission("admin.flags.manage");
const canManageModeration = hasPermission("admin.moderation.manage");
const canManageSearchOps = hasPermission("admin.searchops.manage");
const moderationLoadErr = ref("");
const normalizedSensitiveGroups = computed(() =>
  (Array.isArray(sensitiveGroups.value) ? sensitiveGroups.value : []).map((g, idx) => {
    const words = Array.isArray(g?.words) ? g.words : [];
    const totalWords = Number.isFinite(Number(g?.total_words)) ? Number(g.total_words) : words.length;
    const enabledWords = Number.isFinite(Number(g?.enabled_words))
      ? Number(g.enabled_words)
      : g?.all_enabled
        ? totalWords
        : 0;
    return {
      code: g?.code || `group-${idx}`,
      name: g?.name || g?.code || `分组${idx + 1}`,
      total_words: totalWords,
      enabled_words: enabledWords,
      all_enabled: typeof g?.all_enabled === "boolean" ? g.all_enabled : totalWords > 0 && enabledWords >= totalWords,
      words,
    };
  }),
);

const kpi = computed(() => visual.value?.kpi || {});
const filterOptions = computed(() => visual.value?.filter_options || { categories: [], authors: [], review_statuses: [] });
const trendModules = computed(() => [
  { key: "views", label: "浏览趋势", tone: "views" },
  { key: "likes", label: "点赞趋势", tone: "likes" },
  { key: "comments", label: "评论趋势", tone: "comments" },
  { key: "published_posts", label: "发布趋势", tone: "published" },
]);
const combinedMetrics = computed(() => trendModules.value.map((x) => x.key));
const trendSummary = computed(() => {
  const out = {};
  for (const m of trendModules.value) {
    const total = trends.value.reduce((acc, x) => acc + Number(x?.[m.key] || 0), 0);
    out[m.key] = total;
  }
  return out;
});
const funnel = computed(() => visual.value?.workflow_funnel || []);
const funnelMax = computed(() => Math.max(1, ...funnel.value.map((x) => Number(x.count || 0))));

function fieldMax(field) {
  return Math.max(1, ...trends.value.map((item) => Number(item[field] || 0)));
}

function metricLabel(key) {
  const row = trendModules.value.find((x) => x.key === key);
  return row?.label || key;
}

function toneByMetric(key) {
  return trendModules.value.find((x) => x.key === key)?.tone || "views";
}

function pointX(idx, total, width = 380) {
  if (total <= 1) return Math.round(width / 2);
  return Math.round((idx / (total - 1)) * width);
}

function pointY(value, max, baseY = 130, chartHeight = 110) {
  return Math.round(baseY - (Number(value || 0) / Math.max(1, max)) * chartHeight);
}

function buildLinePath(field, max) {
  if (!trends.value.length) return "";
  const points = trends.value.map((item, idx) => `${pointX(idx, trends.value.length)},${pointY(item[field], max)}`);
  return `M ${points.join(" L ")}`;
}

function buildBars(field, max, width = 380, baseY = 130, chartHeight = 110) {
  const count = trends.value.length || 1;
  const slot = width / count;
  const barW = Math.max(6, Math.min(18, slot * 0.62));
  return trends.value.map((item, idx) => {
    const xCenter = pointX(idx, count, width);
    const h = Math.round((Number(item[field] || 0) / Math.max(1, max)) * chartHeight);
    return {
      x: Math.round(xCenter - barW / 2),
      y: baseY - h,
      w: Math.round(barW),
      h: Math.max(1, h),
    };
  });
}

function buildStackBars(metrics, width = 380, baseY = 130, chartHeight = 110) {
  const totals = trends.value.map((row) => metrics.reduce((acc, m) => acc + Number(row?.[m] || 0), 0));
  const maxTotal = Math.max(1, ...totals);
  const count = trends.value.length || 1;
  const slot = width / count;
  const barW = Math.max(8, Math.min(22, slot * 0.66));
  return trends.value.map((row, idx) => {
    let cursor = baseY;
    const xCenter = pointX(idx, count, width);
    const segments = metrics.map((m) => {
      const v = Number(row?.[m] || 0);
      const h = Math.round((v / maxTotal) * chartHeight);
      cursor -= h;
      return {
        metric: m,
        x: Math.round(xCenter - barW / 2),
        y: Math.round(cursor),
        w: Math.round(barW),
        h: Math.max(1, h),
      };
    });
    return segments;
  });
}

function changeModuleChartType(key, val) {
  moduleChartType.value = { ...moduleChartType.value, [key]: val };
}

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
    const params = {
      start_date: startDate.value,
      end_date: endDate.value,
      category_id: categoryId.value || undefined,
      author_id: authorId.value || undefined,
      review_status: reviewStatus.value === "all" ? undefined : reviewStatus.value,
      group_by: trendGroupBy.value,
    };
    const [res1, res2] = await Promise.all([
      getDashboardVisual(params),
      getDashboardTrends(params),
    ]);
    visual.value = res1.data || null;
    trends.value = res2.data.points || [];
    moderationLoadErr.value = "";
    const [f1, f2, f3, f4] = await Promise.allSettled([
      listFeatureFlags(),
      getModerationLists(),
      getSearchOps(),
      listSensitiveGroups(),
    ]);
    featureFlags.value = f1.status === "fulfilled" ? (f1.value.data || []) : [];
    moderation.value =
      f2.status === "fulfilled"
        ? (f2.value.data || { sensitive_words: [], blacklist_words: [] })
        : { sensitive_words: [], blacklist_words: [] };
    searchOps.value = f3.status === "fulfilled" ? (f3.value.data || { hotwords: [], synonyms: [] }) : { hotwords: [], synonyms: [] };
    if (f4.status === "fulfilled") {
      const raw = f4.value.data;
      if (Array.isArray(raw)) {
        sensitiveGroups.value = raw;
      } else if (raw && typeof raw === "object") {
        // 兼容后端返回 map 结构：{ code: {...} }
        sensitiveGroups.value = Object.values(raw);
      } else {
        sensitiveGroups.value = [];
      }
    } else {
      sensitiveGroups.value = [];
    }
    if (f2.status === "rejected" || f4.status === "rejected") {
      moderationLoadErr.value = "审核策略部分数据加载失败，已降级展示";
    }
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

async function onToggleSensitiveGroup(g) {
  await toggleSensitiveGroup(g.code, !g.all_enabled);
  await load();
}

function shortWords(list, limit = 12) {
  const arr = Array.isArray(list) ? list : [];
  if (arr.length <= limit) return arr.join("、") || "—";
  return `${arr.slice(0, limit).join("、")} ...（共 ${arr.length} 个）`;
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
      category_id: categoryId.value || undefined,
      author_id: authorId.value || undefined,
      review_status: reviewStatus.value === "all" ? undefined : reviewStatus.value,
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
  <section class="admin-page dashboard-page">
    <div class="card">
      <h2>运营看板</h2>
      <div class="dashboard-tabs">
        <button type="button" class="tab-btn" :class="{ active: activeTab === 'overview' }" @click="activeTab = 'overview'">概览</button>
        <button type="button" class="tab-btn" :class="{ active: activeTab === 'trends' }" @click="activeTab = 'trends'">趋势</button>
        <button type="button" class="tab-btn" :class="{ active: activeTab === 'ranking' }" @click="activeTab = 'ranking'">排行</button>
        <button type="button" class="tab-btn" :class="{ active: activeTab === 'strategy' }" @click="activeTab = 'strategy'">运营策略</button>
      </div>
      <div class="admin-toolbar-actions filter-bar">
        <label>开始 <input v-model="startDate" type="date" /></label>
        <label>结束 <input v-model="endDate" type="date" /></label>
        <label
          >分类
          <select v-model="categoryId">
            <option value="">全部</option>
            <option v-for="x in filterOptions.categories || []" :key="x.id" :value="x.id">{{ x.name }}</option>
          </select>
        </label>
        <label
          >作者
          <select v-model="authorId">
            <option value="">全部</option>
            <option v-for="x in filterOptions.authors || []" :key="x.id" :value="x.id">{{ x.name }}</option>
          </select>
        </label>
        <label
          >状态
          <select v-model="reviewStatus">
            <option value="all">全部</option>
            <option value="draft">草稿</option>
            <option value="pending">待审</option>
            <option value="approved">已发布</option>
            <option value="rejected">已拒绝</option>
            <option value="offline">已下线</option>
          </select>
        </label>
        <button type="button" class="secondary" @click="load">刷新</button>
        <button v-if="canExportDashboard" type="button" class="secondary" :disabled="exporting" @click="onExport('csv')">
          导出 CSV
        </button>
        <button v-if="canExportDashboard" type="button" class="secondary" :disabled="exporting" @click="onExport('xlsx')">
          导出 XLSX
        </button>
      </div>
    </div>
    <p v-if="loading" class="meta">加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <div v-else-if="visual" class="dashboard-grid">
      <div v-if="activeTab === 'overview'" class="card kpi-grid">
        <article class="kpi-item">
          <span>文章总数</span>
          <strong>{{ kpi.posts_total || 0 }}</strong>
        </article>
        <article class="kpi-item">
          <span>已发布</span>
          <strong>{{ kpi.published_total || 0 }}</strong>
        </article>
        <article class="kpi-item">
          <span>发布率</span>
          <strong>{{ (kpi.publish_rate || 0).toFixed(2) }}%</strong>
        </article>
        <article class="kpi-item">
          <span>待审核文章</span>
          <strong>{{ kpi.pending_total || 0 }}</strong>
        </article>
        <article class="kpi-item">
          <span>待审核评论</span>
          <strong>{{ kpi.comments_pending || 0 }}</strong>
        </article>
        <article class="kpi-item">
          <span>待处理举报</span>
          <strong>{{ kpi.reports_pending || 0 }}</strong>
        </article>
      </div>

      <div v-if="activeTab === 'trends'" class="card span-2">
        <div class="trend-header">
          <h3>多指标趋势图</h3>
          <div class="trend-toolbar">
            <label>
              展示模式
              <select v-model="trendMode">
                <option value="split">分图展示</option>
                <option value="combined">组合展示</option>
              </select>
            </label>
            <label>
              时间粒度
              <select v-model="trendGroupBy" @change="load">
                <option value="day">按日</option>
                <option value="week">按周</option>
                <option value="month">按月</option>
              </select>
            </label>
          </div>
        </div>
        <div v-if="trendMode === 'combined'" class="trend-combined">
          <div class="trend-module-head">
            <span class="meta">指标组合：浏览/点赞/评论/发布</span>
            <label>
              图形
              <select v-model="combinedChartType">
                <option value="line">折线图</option>
                <option value="bar">柱状图</option>
                <option value="stack">堆叠柱状图</option>
              </select>
            </label>
          </div>
          <svg viewBox="0 0 380 150" class="mini-trend-svg">
            <path d="M 0 130 L 380 130" class="axis" />
            <template v-if="combinedChartType === 'line'">
              <path
                v-for="m in trendModules"
                :key="`line-${m.key}`"
                :d="buildLinePath(m.key, fieldMax(m.key))"
                class="line"
                :class="m.tone"
              />
            </template>
            <template v-else-if="combinedChartType === 'bar'">
              <template v-for="m in trendModules" :key="`bar-${m.key}`">
                <rect
                  v-for="(b, i) in buildBars(m.key, fieldMax(m.key))"
                  :key="`bar-${m.key}-${i}`"
                  class="bar-rect"
                  :class="m.tone"
                  :x="b.x"
                  :y="b.y"
                  :width="Math.max(2, Math.floor(b.w / trendModules.length))"
                  :height="b.h"
                  :transform="`translate(${(trendModules.findIndex((x) => x.key === m.key) - 1.5) * Math.max(2, Math.floor(b.w / trendModules.length))},0)`"
                />
              </template>
            </template>
            <template v-else>
              <template v-for="(bucket, i) in buildStackBars(combinedMetrics)">
                <rect
                  v-for="seg in bucket"
                  :key="`stack-${i}-${seg.metric}`"
                  class="bar-rect"
                  :class="toneByMetric(seg.metric)"
                  :x="seg.x"
                  :y="seg.y"
                  :width="seg.w"
                  :height="seg.h"
                />
              </template>
            </template>
          </svg>
          <div class="trend-legend">
            <span v-for="m in trendModules" :key="`legend-${m.key}`" class="dot" :class="m.tone">{{ m.label }}</span>
          </div>
        </div>
        <div v-else class="trend-modules">
          <article v-for="m in trendModules" :key="m.key" class="trend-module">
            <div class="trend-module-head">
              <span class="dot" :class="m.tone">{{ m.label }}</span>
              <div class="trend-module-right">
                <strong>{{ trendSummary[m.key] || 0 }}</strong>
                <label>
                  图形
                  <select :value="moduleChartType[m.key]" @change="changeModuleChartType(m.key, $event.target.value)">
                    <option value="line">折线图</option>
                    <option value="bar">柱状图</option>
                  </select>
                </label>
              </div>
            </div>
            <svg viewBox="0 0 380 150" class="mini-trend-svg">
              <path d="M 0 130 L 380 130" class="axis" />
              <template v-if="moduleChartType[m.key] === 'line'">
                <path :d="buildLinePath(m.key, fieldMax(m.key))" class="line" :class="m.tone" />
              </template>
              <template v-else>
                <rect
                  v-for="(b, i) in buildBars(m.key, fieldMax(m.key))"
                  :key="`single-${m.key}-${i}`"
                  class="bar-rect"
                  :class="m.tone"
                  :x="b.x"
                  :y="b.y"
                  :width="b.w"
                  :height="b.h"
                />
              </template>
            </svg>
          </article>
        </div>
      </div>

      <div v-if="activeTab === 'overview'" class="card">
        <h3>流程漏斗</h3>
        <div class="funnel">
          <div v-for="x in funnel" :key="x.key" class="funnel-row">
            <span>{{ x.label }}</span>
            <i :style="{ width: `${(Number(x.count || 0) / funnelMax) * 100}%` }"></i>
            <em>{{ x.count }}</em>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'overview'" class="card">
        <h3>分类分布 Top8</h3>
        <ul class="rank-list">
          <li v-for="x in visual.category_distribution || []" :key="x.name">
            <span>{{ x.name }}</span>
            <strong>{{ x.count }}</strong>
          </li>
        </ul>
      </div>

      <div v-if="activeTab === 'overview'" class="card">
        <h3>标签分布 Top8</h3>
        <ul class="rank-list">
          <li v-for="x in visual.tag_distribution || []" :key="x.name">
            <span>{{ x.name }}</span>
            <strong>{{ x.count }}</strong>
          </li>
        </ul>
      </div>

      <div v-if="activeTab === 'ranking'" class="card">
        <h3>热度 Top10</h3>
        <ol class="top-list">
          <li v-for="it in visual.top_hot_posts || []" :key="it.id">
            <span class="title">{{ it.title }}</span>
            <span class="meta">热度 {{ it.hot_score }} / 浏览 {{ it.views }}</span>
          </li>
        </ol>
      </div>

      <div v-if="activeTab === 'ranking'" class="card">
        <h3>风险 Top10</h3>
        <ol class="top-list">
          <li v-for="it in visual.top_risk_posts || []" :key="it.id">
            <span class="title">{{ it.title }}</span>
            <span class="meta">举报 {{ it.report_count }}</span>
          </li>
        </ol>
      </div>

      <div v-if="activeTab === 'strategy'" class="card span-2">
        <h3>运营动作区</h3>
        <div class="ops-row">
          <div>
            <h4>灰度开关</h4>
            <ul>
              <li v-for="f in featureFlags" :key="f.id">
                {{ f.name }}（{{ f.code }}）: {{ f.enabled ? "开启" : "关闭" }}
                <button v-if="canManageFlags" type="button" class="secondary small" @click="toggleFlag(f)">切换</button>
              </li>
            </ul>
          </div>
          <div>
            <h4>审核策略</h4>
            <p>敏感词：{{ shortWords(moderation.sensitive_words) }}</p>
            <p>黑名单词：{{ shortWords(moderation.blacklist_words) }}</p>
            <p v-if="moderationLoadErr" class="error">{{ moderationLoadErr }}</p>
            <div class="group-list">
              <div v-for="g in normalizedSensitiveGroups" :key="g.code" class="group-item">
                <span>{{ g.name }}（{{ g.enabled_words }}/{{ g.total_words }}）</span>
                <button v-if="canManageModeration" type="button" class="secondary small" @click="onToggleSensitiveGroup(g)">
                  {{ g.all_enabled ? "整组停用" : "整组启用" }}
                </button>
              </div>
            </div>
            <div v-if="canManageModeration" class="action-inputs">
              <input v-model="newSensitive" placeholder="新增敏感词" />
              <button type="button" class="secondary" @click="addSensitive">添加敏感词</button>
              <input v-model="newBlacklist" placeholder="新增黑名单词" />
              <button type="button" class="secondary" @click="addBlacklist">添加黑名单词</button>
            </div>
          </div>
          <div>
            <h4>搜索运营</h4>
            <p>热词：{{ (searchOps.hotwords || []).slice(0, 10).map((x) => `${x.keyword}(${x.cnt})`).join("、") || "—" }}</p>
            <ul>
              <li v-for="s in searchOps.synonyms || []" :key="s.id">{{ s.src }} -> {{ s.dst }}</li>
            </ul>
            <div v-if="canManageSearchOps" class="action-inputs">
              <input v-model="newSynSrc" placeholder="同义词原词" />
              <input v-model="newSynDst" placeholder="同义词目标词" />
              <button type="button" class="secondary" @click="addSyn">新增同义词</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.dashboard-page {
  display: grid;
  gap: 0.7rem;
}
.filter-bar {
  margin-top: 0.45rem;
}
.dashboard-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.5rem;
}
.tab-btn {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  border-radius: 999px;
  padding: 0.22rem 0.7rem;
  cursor: pointer;
}
.tab-btn.active {
  border-color: var(--accent);
  color: var(--accent-hover);
  background: color-mix(in srgb, var(--accent) 14%, transparent);
}
.dashboard-grid {
  display: grid;
  gap: 0.7rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.span-2 {
  grid-column: span 2;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
}
.kpi-item {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.6rem;
}
.kpi-item span {
  color: var(--muted);
}
.kpi-item strong {
  display: block;
  margin-top: 0.1rem;
  font-size: 1.2rem;
}
.trend-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  margin-top: 0.45rem;
}
.dot::before {
  content: "";
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
}
.dot.views::before,
.line.views {
  stroke: #2f81f7;
  background: #2f81f7;
}
.dot.likes::before,
.line.likes {
  stroke: #f59e0b;
  background: #f59e0b;
}
.dot.comments::before,
.line.comments {
  stroke: #10b981;
  background: #10b981;
}
.dot.published::before,
.line.published {
  stroke: #a855f7;
  background: #a855f7;
}
.bar-rect {
  opacity: 0.9;
}
.bar-rect.views {
  fill: #2f81f7;
}
.bar-rect.likes {
  fill: #f59e0b;
}
.bar-rect.comments {
  fill: #10b981;
}
.bar-rect.published {
  fill: #a855f7;
}
.trend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.trend-header h3 {
  margin: 0;
}
.trend-toolbar {
  display: flex;
  gap: 0.45rem;
  flex-wrap: wrap;
}
.trend-toolbar label {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--muted);
  font-size: 12px;
}
.trend-toolbar select {
  width: auto;
  min-width: 6.2rem;
}
.trend-chart-wrap {
  margin-top: 0.45rem;
  display: grid;
  grid-template-columns: 36px 1fr;
  gap: 0.35rem;
}
.trend-y {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: var(--muted);
}
.trend-svg {
  width: 100%;
  height: 240px;
}
.trend-modules {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.55rem;
  margin-top: 0.6rem;
}
.trend-combined {
  margin-top: 0.6rem;
}
.trend-module {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.45rem 0.55rem;
}
.trend-module-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}
.trend-module-right {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.trend-module-right strong {
  font-size: 0.95rem;
}
.trend-module-right label {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--muted);
  font-size: 12px;
}
.trend-module-right select {
  width: auto;
  min-width: 5.6rem;
}
.mini-trend-svg {
  width: 100%;
  height: 120px;
}
.axis {
  stroke: var(--border);
  stroke-width: 1;
}
.line {
  fill: none;
  stroke-width: 2.2;
}
.trend-x {
  margin-left: 36px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(36px, 1fr));
  color: var(--muted);
}
.funnel {
  display: grid;
  gap: 0.45rem;
}
.funnel-row {
  display: grid;
  grid-template-columns: 70px 1fr 52px;
  gap: 0.4rem;
  align-items: center;
}
.funnel-row i {
  display: block;
  height: 12px;
  border-radius: 999px;
  background: linear-gradient(90deg, #22c55e, #0ea5e9);
}
.funnel-row em {
  color: var(--muted);
  font-style: normal;
}
.rank-list,
.top-list {
  margin: 0;
  padding-left: 1rem;
}
.rank-list li,
.top-list li {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  margin: 0.2rem 0;
}
.title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ops-row {
  display: grid;
  gap: 0.7rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.action-inputs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}
.group-list {
  margin: 0.35rem 0 0.5rem;
  display: grid;
  gap: 0.35rem;
}
.group-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
@media (max-width: 1100px) {
  .dashboard-grid,
  .ops-row {
    grid-template-columns: 1fr;
  }
  .span-2 {
    grid-column: span 1;
  }
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .trend-modules {
    grid-template-columns: 1fr;
  }
}
</style>
