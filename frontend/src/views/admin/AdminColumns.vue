<script setup>
import { computed, ref } from "vue";
import AdminPaginationBar from "../../components/AdminPaginationBar.vue";
import BaseModal from "../../components/BaseModal.vue";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import { adminListPosts, createColumn, deleteColumn, listColumnsAdmin, updateColumn } from "../../api";
import { useAdminListPage } from "../../composables/useAdminListPage";

const { rows, total, page, pageSize, loading, err, load, setPage, onPageSizeChange } = useAdminListPage({
  listFn: listColumnsAdmin,
  redirectPath: "/admin/columns",
});

// 文章候选集与专栏表单状态。
const posts = ref([]);
const formOpen = ref(false);
const formTitle = ref("");
const editingId = ref(null);
const fName = ref("");
const fSlug = ref("");
const fDesc = ref("");
const fCover = ref("");
const fPublic = ref(true);
/** @type {import('vue').Ref<{ id: number, title: string }[]>} */
const fOrderedPosts = ref([]);
const postPickerQuery = ref("");
const postPickerOpen = ref(false);
const formErr = ref("");
const saving = ref(false);

// 删除确认弹窗状态。
const delOpen = ref(false);
const delRow = ref(null);
const delMsg = ref("");

const availablePosts = computed(() => {
  // 候选文章 = 全量文章 - 已绑定文章，防止重复加入。
  const set = new Set(fOrderedPosts.value.map((x) => x.id));
  return posts.value.filter((p) => !set.has(p.id));
});
const pickerVisiblePosts = computed(() => {
  /** 输入过滤后的候选文章列表。 */
  const kw = postPickerQuery.value.trim().toLowerCase();
  if (!kw) return posts.value;
  return posts.value.filter((p) => String(p.title || "").toLowerCase().includes(kw));
});

async function loadPosts() {
  /** 拉取可绑定文章候选集。 */
  try {
    const { data } = await adminListPosts({ skip: 0, limit: 200 });
    posts.value = data?.items || [];
  } catch {
    posts.value = [];
  }
}

loadPosts();

function resetForm() {
  /** 重置专栏表单到初始状态。 */
  fName.value = "";
  fSlug.value = "";
  fDesc.value = "";
  fCover.value = "";
  fPublic.value = true;
  fOrderedPosts.value = [];
  postPickerQuery.value = "";
  postPickerOpen.value = false;
  formErr.value = "";
}

function openCreate() {
  /** 打开新增专栏弹窗。 */
  editingId.value = null;
  formTitle.value = "新增专栏";
  resetForm();
  formOpen.value = true;
}

function openEdit(r) {
  /** 打开编辑专栏并回填已绑定文章顺序。 */
  editingId.value = r.id;
  formTitle.value = "编辑专栏";
  fName.value = r.name || "";
  fSlug.value = r.slug || "";
  fDesc.value = r.description || "";
  fCover.value = r.cover_image_url || "";
  fPublic.value = !!r.is_public;
  const ids = Array.isArray(r.post_ids) ? r.post_ids : [];
  const titles = Array.isArray(r.post_titles) ? r.post_titles : [];
  fOrderedPosts.value = ids.map((id, i) => ({
    id: Number(id),
    title: titles[i] || `#${id}`,
  }));
  postPickerQuery.value = "";
  postPickerOpen.value = false;
  formErr.value = "";
  formOpen.value = true;
}

function isPostSelected(id) {
  /** 判断文章是否已绑定。 */
  return fOrderedPosts.value.some((x) => x.id === id);
}

function togglePostFromPicker(post) {
  /** 在悬浮层中多选/取消文章绑定。 */
  const id = Number(post?.id);
  if (!Number.isFinite(id) || id <= 0) return;
  if (isPostSelected(id)) {
    fOrderedPosts.value = fOrderedPosts.value.filter((x) => x.id !== id);
    return;
  }
  fOrderedPosts.value = [...fOrderedPosts.value, { id, title: post?.title || `#${id}` }];
}

function openPostPicker() {
  /** 聚焦输入框时，贴边打开文章悬浮层。 */
  postPickerOpen.value = true;
}

function closePostPickerWithDelay() {
  /** 通过延时收起，确保悬浮层内点击不会被 blur 抢先关闭。 */
  window.setTimeout(() => {
    postPickerOpen.value = false;
  }, 120);
}

function removeOrdered(i) {
  /** 从绑定列表移除指定位置文章。 */
  fOrderedPosts.value = fOrderedPosts.value.filter((_, idx) => idx !== i);
}

function moveUp(i) {
  /** 上移绑定文章顺序。 */
  if (i <= 0) return;
  const arr = [...fOrderedPosts.value];
  [arr[i - 1], arr[i]] = [arr[i], arr[i - 1]];
  fOrderedPosts.value = arr;
}

function moveDown(i) {
  /** 下移绑定文章顺序。 */
  if (i >= fOrderedPosts.value.length - 1) return;
  const arr = [...fOrderedPosts.value];
  [arr[i], arr[i + 1]] = [arr[i + 1], arr[i]];
  fOrderedPosts.value = arr;
}

async function save() {
  /** 保存专栏：post_ids 顺序即前台展示顺序。 */
  formErr.value = "";
  const name = fName.value.trim();
  const slug = fSlug.value.trim();
  if (!name || !slug) {
    formErr.value = "请填写名称与 slug";
    return;
  }
  const payload = {
    name,
    slug,
    description: fDesc.value.trim() || null,
    cover_image_url: fCover.value.trim() || null,
    is_public: !!fPublic.value,
    post_ids: fOrderedPosts.value.map((x) => x.id),
  };
  saving.value = true;
  try {
    if (editingId.value == null) await createColumn(payload);
    else await updateColumn(editingId.value, payload);
    formOpen.value = false;
    await load();
  } catch (e) {
    formErr.value = e.response?.data?.detail || e.message || "保存失败";
  } finally {
    saving.value = false;
  }
}

function askDel(r) {
  /** 打开删除专栏确认弹窗。 */
  delRow.value = r;
  delMsg.value = `确定删除专栏「${r.name}」？`;
  delOpen.value = true;
}

async function confirmDel() {
  /** 确认删除专栏并刷新列表。 */
  if (!delRow.value) return;
  try {
    await deleteColumn(delRow.value.id);
    delOpen.value = false;
    await load();
  } catch (e) {
    alert(e.response?.data?.detail || e.message || "删除失败");
  }
}
</script>

<template>
  <div class="admin-page">
    <div class="admin-toolbar">
      <p class="admin-toolbar-desc">维护专栏信息并绑定文章（顺序即前台展示顺序），面向前台专栏频道展示。</p>
      <div class="admin-toolbar-actions">
        <button type="button" @click="openCreate">新增专栏</button>
      </div>
    </div>
    <div class="admin-pagination-wrap">
      <!-- 列表分页：仅在有数据且无错误时展示。 -->
      <AdminPaginationBar
        v-if="!loading && !err && total > 0"
        :total="total"
        :page="page"
        :page-size="pageSize"
        @update:page="setPage"
        @page-size-change="onPageSizeChange"
      />
    </div>
    <p v-if="loading" class="admin-loading">加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <div v-else class="admin-table-scroll">
      <table class="admin-data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>名称</th>
            <th>slug</th>
            <th>是否公开</th>
            <th>文章数</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.id }}</td>
            <td>{{ r.name }}</td>
            <td>{{ r.slug }}</td>
            <td>{{ r.is_public ? "公开" : "私有" }}</td>
            <td>{{ (r.post_ids || []).length }}</td>
            <td class="admin-mono">{{ r.created_at }}</td>
            <td class="admin-ops">
              <a href="#" class="op-link" @click.prevent="openEdit(r)">编辑</a>
              <span class="op-sep"> | </span>
              <a href="#" class="op-link danger-link" @click.prevent="askDel(r)">删除</a>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!rows.length" class="admin-table-empty">暂无专栏。</p>
    </div>

    <BaseModal :open="formOpen" :title="formTitle" wide @close="formOpen = false">
      <!-- 专栏编辑分三段：基础信息、可见性、绑定文章。 -->
      <div class="col-form">
        <section class="form-section">
          <h3 class="section-title">基础信息</h3>
          <div class="field-grid">
            <div class="field">
              <label class="field-label" for="col-name">名称</label>
              <input id="col-name" v-model="fName" class="field-input" type="text" placeholder="专栏名称" />
            </div>
            <div class="field">
              <label class="field-label" for="col-slug">slug</label>
              <input id="col-slug" v-model="fSlug" class="field-input field-input-mono" type="text" placeholder="url 片段，如 my-column" />
            </div>
            <div class="field field-span2">
              <label class="field-label" for="col-cover">封面 URL</label>
              <input id="col-cover" v-model="fCover" class="field-input" type="url" placeholder="https://…" />
            </div>
            <div class="field field-span2">
              <label class="field-label" for="col-desc">简介</label>
              <textarea id="col-desc" v-model="fDesc" class="field-textarea" rows="3" placeholder="可选，前台专栏卡片展示" />
            </div>
          </div>
        </section>

        <section class="form-section">
          <h3 class="section-title">可见性</h3>
          <label class="public-switch">
            <!-- 自定义开关保留原生 checkbox，兼顾可访问性与视觉表现。 -->
            <input v-model="fPublic" type="checkbox" class="public-switch-input" />
            <span class="public-switch-ui" aria-hidden="true" />
            <span class="public-switch-text">
              <span class="public-switch-title">公开可见</span>
              <span class="public-switch-desc">关闭后，前台「专栏」列表与详情中不展示本专栏</span>
            </span>
          </label>
        </section>

        <section class="form-section">
          <h3 class="section-title">绑定文章</h3>
          <p class="section-hint">列表顺序即为前台专栏内文章顺序，可使用右侧按钮调整。</p>

          <div class="bind-panel">
            <div class="add-block">
              <label class="field-label" for="col-post-pick">从文章库添加</label>
              <div class="picker-wrap">
                <div class="picker-input-shell">
                  <input
                    id="col-post-pick"
                    v-model.trim="postPickerQuery"
                    class="field-input"
                    type="text"
                    placeholder="点击并输入关键词筛选文章，支持多选"
                    @focus="openPostPicker"
                    @blur="closePostPickerWithDelay"
                  />
                </div>
                <div v-if="postPickerOpen" class="picker-float" @mousedown.prevent>
                  <p v-if="!pickerVisiblePosts.length" class="picker-empty">未匹配到文章</p>
                  <ul v-else class="picker-list">
                    <li v-for="p in pickerVisiblePosts" :key="p.id" class="picker-item">
                      <label class="picker-option">
                        <input
                          type="checkbox"
                          :checked="isPostSelected(p.id)"
                          @change="togglePostFromPicker(p)"
                        />
                        <span class="picker-title" :title="p.title">{{ p.title }}</span>
                      </label>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            <p v-if="!posts.length" class="bind-empty">暂无可选文章，请先在「文章」中创建并保存。</p>

            <div v-if="fOrderedPosts.length" class="ordered-wrap">
              <!-- 列表顺序即前台专栏详情页文章排序。 -->
              <div class="ordered-head">
                <span>已选 {{ fOrderedPosts.length }} 篇</span>
              </div>
              <ol class="ordered-list">
                <li v-for="(p, idx) in fOrderedPosts" :key="p.id" class="ordered-item">
                  <span class="order-badge">{{ idx + 1 }}</span>
                  <span class="ordered-title" :title="p.title">{{ p.title }}</span>
                  <span class="ordered-actions">
                    <button type="button" class="ord-btn" title="上移" :disabled="idx === 0" @click="moveUp(idx)">↑</button>
                    <button
                      type="button"
                      class="ord-btn"
                      title="下移"
                      :disabled="idx === fOrderedPosts.length - 1"
                      @click="moveDown(idx)"
                    >
                      ↓
                    </button>
                    <button type="button" class="ord-btn ord-btn-remove" title="移除" @click="removeOrdered(idx)">移除</button>
                  </span>
                </li>
              </ol>
            </div>
          </div>
        </section>
      </div>

      <p v-if="formErr" class="error form-err">{{ formErr }}</p>
      <template #footer>
        <button type="button" class="secondary" @click="formOpen = false">取消</button>
        <button type="button" :disabled="saving" @click="save">{{ saving ? "保存中…" : "保存" }}</button>
      </template>
    </BaseModal>

    <ConfirmDialog :open="delOpen" title="删除专栏" :message="delMsg" @close="delOpen = false" @confirm="confirmDel" />
  </div>
</template>

<style scoped>
.op-link {
  color: var(--accent);
  text-decoration: none;
  cursor: pointer;
}
.op-link:hover {
  text-decoration: underline;
}
.danger-link {
  color: #ef4444;
}
.op-sep {
  color: var(--muted);
}

/* —— 专栏表单（宽弹窗） —— */
.col-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  min-width: 0;
}
.form-section {
  min-width: 0;
}
.section-title {
  margin: 0 0 0.65rem;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}
.section-hint {
  margin: -0.25rem 0 0.75rem;
  font-size: 0.85rem;
  color: var(--muted);
  line-height: 1.45;
}

.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem 1rem;
}
@media (max-width: 640px) {
  .field-grid {
    grid-template-columns: 1fr;
  }
}
.field-span2 {
  grid-column: 1 / -1;
}
.field-label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text, #e2e8f0);
}
/* 控件样式由全局 style.css 统一；此处仅保留字号与等宽 */
.field-input,
.field-textarea,
.field-select {
  font-size: 0.9rem;
}
.field-input-mono {
  font-family: ui-monospace, monospace;
  font-size: 0.85rem;
}
.field-textarea {
  min-height: 4.5rem;
}

/* 公开可见：开关行 */
.public-switch {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.15);
  cursor: pointer;
  user-select: none;
}
.public-switch-input {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.public-switch-ui {
  flex-shrink: 0;
  margin-top: 0.1rem;
  width: 2.5rem;
  height: 1.35rem;
  border-radius: 999px;
  background: var(--border);
  position: relative;
  transition: background 0.2s ease;
}
.public-switch-ui::after {
  content: "";
  position: absolute;
  top: 2px;
  left: 2px;
  width: calc(1.35rem - 4px);
  height: calc(1.35rem - 4px);
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.35);
  transition: transform 0.2s ease;
}
.public-switch-input:checked + .public-switch-ui {
  background: var(--accent, #5b9bd5);
}
.public-switch-input:checked + .public-switch-ui::after {
  transform: translateX(1.15rem);
}
.public-switch-input:focus-visible + .public-switch-ui {
  box-shadow: 0 0 0 2px rgba(91, 155, 213, 0.45);
}
.public-switch-text {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}
.public-switch-title {
  font-size: 0.95rem;
  font-weight: 600;
}
.public-switch-desc {
  font-size: 0.8rem;
  color: var(--muted);
  line-height: 1.4;
}

/* 绑定文章 */
.bind-panel {
  padding: 1rem;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.12);
}
.add-block {
  margin-bottom: 0.75rem;
}
.picker-wrap {
  position: relative;
}
.picker-input-shell {
  min-width: 0;
}
.picker-float {
  position: absolute;
  top: calc(100% - 1px);
  left: 0;
  right: 0;
  z-index: 40;
  max-height: 15rem;
  overflow: auto;
  border: 1px solid color-mix(in srgb, var(--accent) 35%, var(--border));
  border-radius: 0 0 10px 10px;
  border-top: none;
  background: var(--surface);
  box-shadow: 0 10px 24px rgba(2, 6, 23, 0.35);
}
.picker-list {
  margin: 0;
  padding: 0.25rem 0;
  list-style: none;
}
.picker-item + .picker-item {
  border-top: 1px solid color-mix(in srgb, var(--border) 70%, transparent);
}
.picker-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  margin: 0;
  padding: 0.45rem 0.65rem;
  cursor: pointer;
}
.picker-option:hover {
  background: color-mix(in srgb, var(--accent) 10%, transparent);
}
.picker-title {
  min-width: 0;
  font-size: 0.86rem;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.picker-empty {
  margin: 0;
  padding: 0.65rem 0.75rem;
  color: var(--muted);
  font-size: 0.85rem;
}
.bind-empty {
  margin: 0;
  font-size: 0.85rem;
  color: var(--muted);
  line-height: 1.45;
}

.ordered-wrap {
  margin-top: 0.5rem;
}
.ordered-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--muted);
}
.ordered-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.ordered-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.6rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface, rgba(15, 23, 42, 0.6));
}
.order-badge {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  display: grid;
  place-items: center;
  font-size: 0.75rem;
  font-weight: 700;
  border-radius: 6px;
  background: rgba(91, 155, 213, 0.2);
  color: var(--accent);
}
.ordered-title {
  flex: 1;
  min-width: 0;
  font-size: 0.88rem;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ordered-actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
  align-items: center;
}
.ord-btn {
  padding: 0.25rem 0.45rem;
  font-size: 0.8rem;
  line-height: 1.2;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: transparent;
  color: var(--text);
  cursor: pointer;
}
.ord-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.ord-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.ord-btn-remove {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  color: #f87171;
  border-color: rgba(248, 113, 113, 0.35);
}
.ord-btn-remove:hover:not(:disabled) {
  background: rgba(248, 113, 113, 0.12);
}

.form-err {
  margin-top: 0.75rem;
}
</style>
