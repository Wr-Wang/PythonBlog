<script setup>
import { computed, ref } from "vue";
import {
  batchWorkflowAction,
  listWorkflowReasonTemplates,
  getWorkflowSlaSummary,
  listWorkflowTaskAudits,
  listWorkflowTasks,
  transitionPost,
} from "../../api";
import AdminPaginationBar from "../../components/AdminPaginationBar.vue";
import { useAdminListPage } from "../../composables/useAdminListPage";

// 列表筛选与批量操作状态。
const taskType = ref("all");
const status = ref("all");
const keyword = ref("");
const startDate = ref("");
const endDate = ref("");
const selectedIds = ref([]);
const batchAction = ref("approve");
const batchAssigneeId = ref("");
const reasonTemplates = ref([]);
const reasonTemplateId = ref("");
const batchRemark = ref("");
const batchResultHint = ref("");
const batchFailExamples = ref("");
const auditOpen = ref(false);
const auditLoading = ref(false);
const auditTaskId = ref("");
const auditRecords = ref([]);
// SLA 概览独立加载状态（与主列表分离）。
const loadingSla = ref(false);
const sla = ref({
  pending_count: 0,
  timeout_count: 0,
  processed_today: 0,
  avg_process_hours: 0,
});

const selectedCount = computed(() => selectedIds.value.length);
const allChecked = computed(() => rows.value.length > 0 && rows.value.every((x) => selectedIds.value.includes(x.id)));
const statusOptions = [
  { value: "all", label: "全部状态" },
  { value: "pending", label: "待处理" },
  { value: "approved", label: "已通过" },
  { value: "rejected", label: "已驳回" },
  { value: "offline", label: "已下线" },
  { value: "open", label: "待处理举报" },
  { value: "closed", label: "已处理举报" },
];

/** 加载 SLA 概览，失败不阻断主列表渲染。 */
async function loadSla(params) {
  loadingSla.value = true;
  try {
    const { data: slaData } = await getWorkflowSlaSummary(params);
    sla.value = { ...sla.value, ...(slaData || {}) };
  } catch (e) {
    // SLA 失败不阻断主列表；保留之前数值并提示错误。
    err.value = e.response?.data?.detail || e.message || "SLA 加载失败";
  } finally {
    loadingSla.value = false;
  }
}

const {
  loading,
  err,
  rows,
  total,
  page,
  pageSize,
  load,
  setPage,
  onPageSizeChange,
} = useAdminListPage({
  listFn: listWorkflowTasks,
  redirectPath: "/admin/workflow",
  // 将页面筛选状态映射为后端查询参数。
  buildListParams: ({ page, pageSize }) => ({
    task_type: taskType.value,
    status: status.value,
    keyword: keyword.value.trim() || undefined,
    start_date: startDate.value || undefined,
    end_date: endDate.value || undefined,
    page,
    size: pageSize,
  }),
  extractItems: (data) => data?.items || [],
  extractTotal: (data) => Number(data?.total || 0),
  // 主列表每次加载后，同步刷新 SLA 与已选任务集合。
  onLoaded: async ({ params, rows }) => {
    selectedIds.value = selectedIds.value.filter((id) => rows.some((x) => x.id === id));
    await loadSla(params);
  },
});

async function loadReasonTemplates() {
  /** 读取审核意见模板；失败时降级为空数组。 */
  try {
    const { data } = await listWorkflowReasonTemplates();
    reasonTemplates.value = Array.isArray(data) ? data : [];
  } catch {
    reasonTemplates.value = [];
  }
}

async function move(post, toStatus) {
  /** 单条快捷流转（当前仅支持 post 任务）。 */
  try {
    if (post.task_type !== "post") {
      err.value = "当前仅支持文章任务流转，评论/举报动作后续补齐";
      return;
    }
    await transitionPost(post.biz_id, toStatus);
    await load();
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "流转失败";
  }
}

function toggleAll() {
  /** 全选/全不选当前页任务。 */
  if (allChecked.value) {
    selectedIds.value = [];
  } else {
    selectedIds.value = rows.value.map((x) => x.id);
  }
}

async function doBatchAction() {
  /** 执行批量动作，并回显失败分布与失败样本。 */
  if (!selectedIds.value.length) {
    err.value = "请先选择要操作的任务";
    return;
  }
  if (!confirm(`确认对 ${selectedIds.value.length} 条任务执行 ${batchAction.value} 操作吗？`)) return;
  try {
    const payload = {
      task_ids: selectedIds.value,
      action: batchAction.value,
      reason_template_id: reasonTemplateId.value ? Number(reasonTemplateId.value) : null,
      remark: batchRemark.value.trim() || null,
      assignee_id: batchAction.value === "reassign" ? Number(batchAssigneeId.value || 0) || null : null,
    };
    const { data } = await batchWorkflowAction(payload);
    const failed = Array.isArray(data?.details) ? data.details.filter((x) => !x.ok) : [];
    if (failed.length) {
      // 失败分布：按后端 error_code 聚合，便于快速识别错误类型。
      const grouped = failed.reduce((acc, item) => {
        const code = item.error_code || "UNKNOWN";
        acc[code] = (acc[code] || 0) + 1;
        return acc;
      }, {});
      const parts = Object.entries(grouped).map(([code, count]) => `${code} x${count}`);
      batchResultHint.value = `失败分布：${parts.join("，")}`;
      const examples = data?.failed_examples && typeof data.failed_examples === "object" ? data.failed_examples : {};
      // 失败样本：每类展示少量 task_id，帮助运维快速复核。
      const exampleParts = Object.entries(examples)
        .filter(([, ids]) => Array.isArray(ids) && ids.length > 0)
        .map(([code, ids]) => `${code}: ${(ids || []).join("、")}`);
      batchFailExamples.value = exampleParts.length ? `失败样本：${exampleParts.join("；")}` : "";
      err.value = `部分成功：成功 ${data.success_count}，失败 ${data.fail_count}`;
    } else {
      batchResultHint.value = `批量执行成功：共 ${data.success_count} 条`;
      batchFailExamples.value = "";
      err.value = "";
    }
    selectedIds.value = [];
    batchRemark.value = "";
    await load();
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "批量操作失败";
  }
}

async function openAudit(taskId) {
  /** 打开并加载任务审计抽屉。 */
  auditOpen.value = true;
  auditTaskId.value = taskId;
  auditLoading.value = true;
  auditRecords.value = [];
  try {
    const { data } = await listWorkflowTaskAudits(taskId);
    auditRecords.value = data?.records || [];
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载审计失败";
  } finally {
    auditLoading.value = false;
  }
}

function onSearch() {
  /** 应用筛选条件；优先重置到第一页。 */
  batchResultHint.value = "";
  batchFailExamples.value = "";
  if (page.value !== 1) setPage(1);
  else load();
}

function resetFilters() {
  /** 重置筛选到默认值并触发查询。 */
  taskType.value = "all";
  status.value = "all";
  keyword.value = "";
  startDate.value = "";
  endDate.value = "";
  onSearch();
}

// 初始化：模板列表与分页首屏由各自入口加载。
loadReasonTemplates();
</script>

<template>
  <section class="admin-page">
    <!-- SLA/KPI 顶部概览区。 -->
    <div class="kpi-grid">
      <article class="card kpi-item">
        <span>待处理任务</span>
        <strong>{{ sla.pending_count }}</strong>
      </article>
      <article class="card kpi-item">
        <span>超时任务</span>
        <strong>{{ sla.timeout_count }}</strong>
      </article>
      <article class="card kpi-item">
        <span>今日处理</span>
        <strong>{{ sla.processed_today }}</strong>
      </article>
      <article class="card kpi-item">
        <span>平均处理时长</span>
        <strong>{{ Number(sla.avg_process_hours || 0).toFixed(2) }}h</strong>
      </article>
    </div>
    <div class="card">
      <h2>流程中心</h2>
      <div class="admin-toolbar-actions">
        <!-- 查询条件：任务类型/状态/关键词/时间范围。 -->
        <select v-model="taskType">
          <option value="all">全部任务</option>
          <option value="post">文章审核</option>
          <option value="comment">评论审核</option>
          <option value="report">举报处理</option>
        </select>
        <select v-model="status">
          <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <input v-model="keyword" type="text" placeholder="标题/内容关键字" />
        <input v-model="startDate" type="date" />
        <input v-model="endDate" type="date" />
        <button type="button" class="secondary" @click="onSearch">查询</button>
        <button type="button" class="secondary" @click="resetFilters">重置</button>
      </div>
      <div class="admin-toolbar-actions batch-bar">
        <!-- 批量操作区：动作、模板、备注、转派人。 -->
        <span class="meta">已选择 {{ selectedCount }} 条</span>
        <select v-model="batchAction">
          <option value="approve">批量通过</option>
          <option value="reject">批量驳回</option>
          <option value="offline">批量下线</option>
          <option value="reassign">批量转派</option>
        </select>
        <select v-model="reasonTemplateId">
          <option value="">审核意见模板（可选）</option>
          <option v-for="tpl in reasonTemplates" :key="tpl.id" :value="tpl.id">{{ tpl.name }}</option>
        </select>
        <input v-model="batchRemark" type="text" placeholder="补充备注（可选）" />
        <input v-if="batchAction === 'reassign'" v-model="batchAssigneeId" type="number" min="1" placeholder="转派用户ID" />
        <button type="button" class="secondary" @click="doBatchAction">执行批量操作</button>
      </div>
      <p v-if="batchResultHint" class="meta">{{ batchResultHint }}</p>
      <p v-if="batchFailExamples" class="meta">{{ batchFailExamples }}</p>
    </div>
    <p v-if="loading" class="meta">加载中…</p>
    <p v-else-if="loadingSla" class="meta">SLA 加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <div v-else class="card admin-table-scroll">
      <table class="admin-data-table admin-data-table-posts">
        <thead>
          <tr>
            <th>
              <input type="checkbox" :checked="allChecked" @change="toggleAll" />
            </th>
            <th>任务ID</th>
            <th>类型</th>
            <th>标题</th>
            <th>状态</th>
            <th>优先级</th>
            <th>处理人</th>
            <th>SLA 截止</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in rows" :key="p.id">
            <td>
              <input v-model="selectedIds" type="checkbox" :value="p.id" />
            </td>
            <td>{{ p.id }}</td>
            <td>{{ p.task_type }}</td>
            <td>{{ p.title }}</td>
            <td>
              {{ p.status }}
              <span v-if="p.is_timeout" class="timeout-tag">超时</span>
            </td>
            <td>{{ p.priority }}</td>
            <td>{{ p.assignee_name || "-" }}</td>
            <td>{{ p.sla_deadline?.replace("T", " ") || "-" }}</td>
            <td>{{ p.created_at?.replace("T", " ") || "-" }}</td>
            <td>
              <!-- 仅文章任务开放快捷流转，其他任务暂保留审计入口。 -->
              <template v-if="p.task_type === 'post'">
                <a href="#" class="op-link" @click.prevent="move(p, 'pending')">送审</a>
                <span class="op-sep"> | </span>
                <a href="#" class="op-link" @click.prevent="move(p, 'approved')">通过</a>
                <span class="op-sep"> | </span>
                <a href="#" class="op-link" @click.prevent="move(p, 'rejected')">驳回</a>
                <span class="op-sep"> | </span>
                <a href="#" class="op-link" @click.prevent="move(p, 'offline')">下线</a>
                <span class="op-sep"> | </span>
                <a href="#" class="op-link" @click.prevent="openAudit(p.id)">审计</a>
              </template>
              <template v-else>
                <span class="meta">待扩展</span>
                <span class="op-sep"> | </span>
                <a href="#" class="op-link" @click.prevent="openAudit(p.id)">审计</a>
              </template>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="10" class="admin-table-empty">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="admin-pagination-wrap">
      <AdminPaginationBar
        :total="total"
        :page="page"
        :page-size="pageSize"
        @update:page="setPage"
        @page-size-change="onPageSizeChange"
      />
    </div>
    <div v-if="auditOpen" class="audit-drawer">
      <!-- 审计抽屉：展示单任务历史动作链。 -->
      <div class="card">
        <div class="audit-head">
          <h3>任务审计：{{ auditTaskId }}</h3>
          <a href="#" class="op-link" @click.prevent="auditOpen = false">关闭</a>
        </div>
        <p v-if="auditLoading" class="meta">加载中…</p>
        <ul v-else class="audit-list">
          <li v-for="x in auditRecords" :key="x.id">
            <strong>{{ x.action }}</strong>
            <span>{{ x.from_status || "-" }} -> {{ x.to_status || "-" }}</span>
            <span>{{ x.operator_name }}</span>
            <span>{{ x.created_at?.replace("T", " ") }}</span>
            <span>{{ x.remark || "-" }}</span>
          </li>
          <li v-if="!auditRecords.length" class="meta">暂无审计记录</li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.6rem;
  margin-bottom: 0.6rem;
}
.kpi-item span {
  color: var(--muted);
}
.kpi-item strong {
  display: block;
  margin-top: 0.2rem;
  font-size: 1.2rem;
}
.op-link {
  color: var(--accent);
  text-decoration: none;
  cursor: pointer;
}
.op-link:hover {
  text-decoration: underline;
}
.op-sep {
  color: var(--muted);
}
.timeout-tag {
  margin-left: 0.25rem;
  color: var(--danger);
}
.batch-bar {
  margin-top: 0.5rem;
}
.audit-drawer {
  margin-top: 0.7rem;
}
.audit-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.audit-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.35rem;
}
.audit-list li {
  display: grid;
  grid-template-columns: 90px 140px 120px 170px 1fr;
  gap: 0.5rem;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.35rem 0.45rem;
}
@media (max-width: 1100px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
