<script setup>
import { ref, watch } from "vue";
import { useRouter } from "vue-router";
import { marked } from "marked";
import AdminPaginationBar from "../../components/AdminPaginationBar.vue";
import BaseModal from "../../components/BaseModal.vue";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import RichTextEditor from "../../components/RichTextEditor.vue";
import { postBodyLooksLikeHtml } from "../../utils/postBodyRender";
import {
  adminListPosts,
  createPost,
  deletePost,
  listCategoriesAdmin,
  listTagsAdmin,
  transitionPost,
  updatePost,
  uploadImage,
} from "../../api";
import { hasPermission } from "../../utils/permissions";

const router = useRouter();
const rows = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const categories = ref([]);
const tags = ref([]);
const loading = ref(true);
const err = ref("");
const q = ref("");
const fReviewStatus = ref("");
const fPublishedOnly = ref("");
const fSortBy = ref("created_at");
const fSortDir = ref("desc");
const fPinnedOnly = ref("");
const fFeaturedOnly = ref("");
const fCategoryFilter = ref("");
const fTagFilter = ref("");

const formOpen = ref(false);
const formTitle = ref("新增文章");
const editingId = ref(null);
const fTitle = ref("");
const fSlug = ref("");
const fExcerpt = ref("");
const fContent = ref("");
const fPublished = ref(false);
const fCategoryId = ref("");
const fTagIds = ref([]);
const fCoverUrl = ref("");
const fReviewStatusEdit = ref("draft");
const fWeight = ref(0);
const fRankLevel = ref(1);
const fIsPinned = ref(false);
const fIsFeatured = ref(false);
const fPublishedAt = ref("");
const fOfflineAt = ref("");
const fContentType = ref("");
const fSourceUrl = ref("");
const formErr = ref("");
const saving = ref(false);

const delOpen = ref(false);
const delTarget = ref(null);
const delMsg = ref("");
const canViewPosts = hasPermission("admin.posts.view");
const canCreatePost = hasPermission("admin.posts.create");
const canEditPost = hasPermission("admin.posts.update");
const canDeletePost = hasPermission("admin.posts.delete");
const canPinPost = hasPermission("admin.posts.pin.update");
const canFeaturePost = hasPermission("admin.posts.featured.update");
const canPublishNow = hasPermission("admin.posts.publish.now");
const canOfflineNow = hasPermission("admin.posts.offline.now");

function tagChecked(id) {
  return fTagIds.value.includes(id);
}
function toggleTag(id) {
  const i = fTagIds.value.indexOf(id);
  if (i >= 0) fTagIds.value = fTagIds.value.filter((x) => x !== id);
  else fTagIds.value = [...fTagIds.value, id];
}

async function loadMeta() {
  const [c, t] = await Promise.all([
    listCategoriesAdmin({ limit: 500 }),
    listTagsAdmin({ limit: 500 }),
  ]);
  categories.value = c.data.items ?? c.data;
  tags.value = t.data.items ?? t.data;
}

async function load() {
  loading.value = true;
  err.value = "";
  if (!canViewPosts) {
    loading.value = false;
    err.value = "缺少权限: admin.posts.view";
    return;
  }
  try {
    await loadMeta();
    let p = page.value;
    const skip = (p - 1) * pageSize.value;
    const params = {
      skip,
      limit: pageSize.value,
      q: q.value.trim() || undefined,
      review_status: fReviewStatus.value || undefined,
      published: fPublishedOnly.value === "" ? undefined : fPublishedOnly.value === "true",
      category_id: fCategoryFilter.value ? Number(fCategoryFilter.value) : undefined,
      tag_id: fTagFilter.value ? Number(fTagFilter.value) : undefined,
      is_pinned: fPinnedOnly.value === "" ? undefined : fPinnedOnly.value === "true",
      is_featured: fFeaturedOnly.value === "" ? undefined : fFeaturedOnly.value === "true",
      sort_by: fSortBy.value,
      sort_dir: fSortDir.value,
    };
    let { data } = await adminListPosts(params);
    const maxP = Math.max(1, Math.ceil(data.total / pageSize.value) || 1);
    if (p > maxP && data.total >= 0) {
      page.value = maxP;
      p = maxP;
      ({ data } = await adminListPosts({ ...params, skip: (p - 1) * pageSize.value }));
    }
    rows.value = data.items;
    total.value = data.total;
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载失败";
    if (e.response?.status === 401) {
      localStorage.removeItem("blog_token");
      router.push({ name: "admin-login", query: { redirect: "/admin/posts" } });
    }
  } finally {
    loading.value = false;
  }
}

watch(page, load, { immediate: true });

function setPage(v) {
  page.value = v;
}

function onPageSizeChange(newSize) {
  pageSize.value = newSize;
  if (page.value !== 1) page.value = 1;
  else load();
}

function applyFilters() {
  if (page.value !== 1) page.value = 1;
  else load();
}

function openCreate() {
  editingId.value = null;
  formTitle.value = "新增文章";
  fTitle.value = "";
  fSlug.value = "";
  fExcerpt.value = "";
  fContent.value = "";
  fPublished.value = false;
  fCategoryId.value = "";
  fTagIds.value = [];
  fCoverUrl.value = "";
  fReviewStatusEdit.value = "draft";
  fWeight.value = 0;
  fRankLevel.value = 1;
  fIsPinned.value = false;
  fIsFeatured.value = false;
  fPublishedAt.value = "";
  fOfflineAt.value = "";
  fContentType.value = "";
  fSourceUrl.value = "";
  formErr.value = "";
  formOpen.value = true;
}

function openEdit(row) {
  editingId.value = row.id;
  formTitle.value = "编辑文章";
  fTitle.value = row.title;
  fSlug.value = row.slug;
  fExcerpt.value = row.excerpt || "";
  fContent.value = normalizeEditorContent(row.content);
  fPublished.value = row.published;
  fCategoryId.value = row.category_id != null ? String(row.category_id) : "";
  fTagIds.value = [...(row.tag_ids || [])];
  fCoverUrl.value = row.cover_image_url || "";
  fReviewStatusEdit.value = row.review_status || "draft";
  fWeight.value = Number(row.weight || 0);
  fRankLevel.value = Number(row.rank_level || 1);
  fIsPinned.value = !!row.is_pinned;
  fIsFeatured.value = !!row.is_featured;
  fPublishedAt.value = toLocalDateTime(row.published_at);
  fOfflineAt.value = toLocalDateTime(row.offline_at);
  fContentType.value = row.content_type || "";
  fSourceUrl.value = row.source_url || "";
  formErr.value = "";
  formOpen.value = true;
}

function suggestSlug() {
  const t = fTitle.value.trim();
  if (!t || editingId.value) return;
  const s = t
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9\u4e00-\u9fa5-]/g, "")
    .slice(0, 80);
  if (s) fSlug.value = s;
}

async function onPickCover(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  formErr.value = "";
  try {
    const { data } = await uploadImage(file);
    fCoverUrl.value = data.url;
  } catch (ex) {
    formErr.value = ex.response?.data?.detail || ex.message || "上传失败";
  }
  e.target.value = "";
}

async function saveForm() {
  formErr.value = "";
  const body = {
    title: fTitle.value.trim(),
    slug: fSlug.value.trim(),
    excerpt: fExcerpt.value.trim() || null,
    content: fContent.value,
    published: fPublished.value,
    category_id: fCategoryId.value === "" ? null : Number(fCategoryId.value),
    cover_image_url: fCoverUrl.value.trim() || null,
    tag_ids: [...fTagIds.value],
    review_status: fReviewStatusEdit.value,
    weight: Number(fWeight.value || 0),
    rank_level: Number(fRankLevel.value || 1),
    is_pinned: !!fIsPinned.value,
    is_featured: !!fIsFeatured.value,
    published_at: fromLocalDateTime(fPublishedAt.value),
    offline_at: fromLocalDateTime(fOfflineAt.value),
    content_type: fContentType.value.trim() || null,
    source_url: fSourceUrl.value.trim() || null,
  };
  if (!body.title || !body.slug || isRichTextEmpty(body.content)) {
    formErr.value = "请填写标题、slug 与正文";
    return;
  }
  saving.value = true;
  try {
    if (editingId.value == null) {
      await createPost(body);
    } else {
      await updatePost(editingId.value, body);
    }
    formOpen.value = false;
    await load();
  } catch (e) {
    formErr.value = e.response?.data?.detail || e.message || "保存失败";
  } finally {
    saving.value = false;
  }
}

function askDelete(row) {
  delTarget.value = row;
  delMsg.value = `确定删除文章「${row.title}」（id=${row.id}）？此操作不可恢复。`;
  delOpen.value = true;
}

async function confirmDelete() {
  if (!delTarget.value) return;
  try {
    await deletePost(delTarget.value.id);
    delOpen.value = false;
    delTarget.value = null;
    await load();
  } catch (e) {
    alert(e.response?.data?.detail || e.message || "删除失败");
  }
}

/** 旧 Markdown 正文打开编辑时转为 HTML，便于在 Quill 中继续编辑 */
function normalizeEditorContent(raw) {
  if (raw == null || raw === "") return "";
  if (postBodyLooksLikeHtml(raw)) return raw;
  try {
    return marked.parse(String(raw), { async: false });
  } catch {
    return `<p>${String(raw)}</p>`;
  }
}

function isRichTextEmpty(html) {
  if (html == null || !String(html).trim()) return true;
  const t = String(html)
    .replace(/<br\s*\/?>/gi, "")
    .replace(/<p>\s*<\/p>/gi, "")
    .replace(/<div>\s*<\/div>/gi, "")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/gi, " ")
    .trim();
  return !t;
}

function toLocalDateTime(v) {
  if (!v) return "";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalDateTime(v) {
  if (!v) return null;
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

async function quickTogglePinned(row) {
  await updatePost(row.id, { is_pinned: !row.is_pinned });
  await load();
}

async function quickToggleFeatured(row) {
  await updatePost(row.id, { is_featured: !row.is_featured });
  await load();
}

async function quickTransition(row, toStatus) {
  await transitionPost(row.id, toStatus);
  await load();
}
</script>

<template>
  <div class="admin-page">
    <div class="admin-toolbar">
      <p class="admin-toolbar-desc">
        正文为富文本（图文、视频嵌入、表情）；旧文章若为 Markdown，打开编辑时会自动转为 HTML 保存。访客仅可见已发布文章。
      </p>
      <div class="admin-toolbar-actions">
        <input v-model="q" placeholder="搜索标题/slug/摘要" />
        <select v-model="fReviewStatus">
          <option value="">审核状态：全部</option>
          <option value="draft">draft</option>
          <option value="pending">pending</option>
          <option value="approved">approved</option>
          <option value="rejected">rejected</option>
          <option value="offline">offline</option>
        </select>
        <select v-model="fPublishedOnly">
          <option value="">发布：全部</option>
          <option value="true">仅已发布</option>
          <option value="false">仅未发布</option>
        </select>
        <select v-model="fPinnedOnly">
          <option value="">置顶：全部</option>
          <option value="true">仅置顶</option>
          <option value="false">仅非置顶</option>
        </select>
        <select v-model="fFeaturedOnly">
          <option value="">精选：全部</option>
          <option value="true">仅精选</option>
          <option value="false">仅非精选</option>
        </select>
        <select v-model="fCategoryFilter">
          <option value="">分类：全部</option>
          <option v-for="c in categories" :key="'fc-' + c.id" :value="String(c.id)">{{ c.name }}</option>
        </select>
        <select v-model="fTagFilter">
          <option value="">标签：全部</option>
          <option v-for="t in tags" :key="'ft-' + t.id" :value="String(t.id)">{{ t.name }}</option>
        </select>
        <select v-model="fSortBy">
          <option value="created_at">排序：创建时间</option>
          <option value="hot_score">排序：热度</option>
          <option value="weight">排序：权重</option>
          <option value="view_count">排序：浏览量</option>
          <option value="published_at">排序：发布时间</option>
        </select>
        <select v-model="fSortDir">
          <option value="desc">降序</option>
          <option value="asc">升序</option>
        </select>
        <button type="button" class="secondary" @click="applyFilters">筛选</button>
        <button v-if="canCreatePost" type="button" @click="openCreate">新增文章</button>
      </div>
    </div>
    <div class="admin-pagination-wrap">
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
      <table class="admin-data-table admin-data-table-posts">
        <thead>
          <tr>
            <th>编号</th>
            <th>标题</th>
            <th>URL 标识</th>
            <th>摘要</th>
            <th>发布</th>
            <th>审核</th>
            <th>置顶</th>
            <th>精选</th>
            <th>权重</th>
            <th>热度</th>
            <th>封面图 URL</th>
            <th>创建时间</th>
            <th>更新时间</th>
            <th>作者</th>
            <th>分类</th>
            <th class="col-tags">标签</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.id }}</td>
            <td class="admin-cell-clip">{{ r.title }}</td>
            <td class="admin-cell-clip">{{ r.slug }}</td>
            <td class="admin-cell-clip">{{ r.excerpt || "—" }}</td>
            <td>{{ r.published }}</td>
            <td>{{ r.review_status || "draft" }}</td>
            <td>{{ r.is_pinned ? "是" : "否" }}</td>
            <td>{{ r.is_featured ? "是" : "否" }}</td>
            <td>{{ r.weight ?? 0 }}</td>
            <td>{{ r.hot_score ?? 0 }}</td>
            <td class="admin-cell-clip admin-mono">{{ r.cover_image_url || "—" }}</td>
            <td class="admin-mono">{{ r.created_at }}</td>
            <td class="admin-mono">{{ r.updated_at }}</td>
            <td>{{ r.author_name || "—" }}</td>
            <td>{{ r.category_name || "—" }}</td>
            <td class="tags-cell">
              <template v-if="r.tag_names?.length">
                <span v-for="(name, i) in r.tag_names" :key="i" class="tag-pill">{{ name }}</span>
              </template>
              <span v-else class="tags-empty">—</span>
            </td>
            <td class="admin-ops">
              <a v-if="canEditPost" href="#" class="op-link" @click.prevent="openEdit(r)">编辑</a>
              <span v-if="canEditPost && (canPinPost || canFeaturePost || canPublishNow || canOfflineNow || canDeletePost)" class="op-sep"> | </span>
              <a v-if="canPinPost" href="#" class="op-link" @click.prevent="quickTogglePinned(r)">{{ r.is_pinned ? "取消置顶" : "置顶" }}</a>
              <span v-if="canPinPost && (canFeaturePost || canPublishNow || canOfflineNow || canDeletePost)" class="op-sep"> | </span>
              <a v-if="canFeaturePost" href="#" class="op-link" @click.prevent="quickToggleFeatured(r)">{{ r.is_featured ? "取消精选" : "设为精选" }}</a>
              <span v-if="canFeaturePost && (canPublishNow || canOfflineNow || canDeletePost)" class="op-sep"> | </span>
              <a v-if="canPublishNow" href="#" class="op-link" @click.prevent="quickTransition(r, 'approved')">立即发布</a>
              <span v-if="canPublishNow && (canOfflineNow || canDeletePost)" class="op-sep"> | </span>
              <a v-if="canOfflineNow" href="#" class="op-link" @click.prevent="quickTransition(r, 'offline')">立即下线</a>
              <span v-if="canOfflineNow && canDeletePost" class="op-sep"> | </span>
              <a v-if="canDeletePost" href="#" class="op-link danger-link" @click.prevent="askDelete(r)">删除</a>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!rows.length" class="admin-table-empty">暂无文章，点击「新增文章」开始。</p>
    </div>

    <BaseModal :open="formOpen" :title="formTitle" wide @close="formOpen = false">
      <div class="form-grid">
        <label>标题 <input v-model="fTitle" @blur="suggestSlug" /></label>
        <label>slug <input v-model="fSlug" /></label>
        <label>摘要 <input v-model="fExcerpt" /></label>
        <div class="full rte-field">
          <span class="rte-label">正文（富文本）</span>
          <RichTextEditor v-model="fContent" />
        </div>
        <label>分类
          <select v-model="fCategoryId">
            <option value="">—</option>
            <option v-for="c in categories" :key="c.id" :value="String(c.id)">
              {{ c.id }} — {{ c.name }}
            </option>
          </select>
        </label>
        <div class="form-field full">
          <span class="form-field-label">标签（多选）</span>
          <div class="tags-grid" role="group" aria-label="标签（多选）">
            <label v-for="t in tags" :key="t.id" class="tag-chk">
              <input type="checkbox" :checked="tagChecked(t.id)" @change="toggleTag(t.id)" />
              <span class="tag-chip-name">{{ t.name }}</span>
              <span class="tag-chip-slug" :title="'URL 标识：' + t.slug">{{ t.slug }}</span>
            </label>
          </div>
        </div>
        <label class="full">封面图 URL <input v-model="fCoverUrl" placeholder="/uploads/xxx.jpg" /></label>
        <label>审核状态
          <select v-model="fReviewStatusEdit">
            <option value="draft">draft</option>
            <option value="pending">pending</option>
            <option value="approved">approved</option>
            <option value="rejected">rejected</option>
            <option value="offline">offline</option>
          </select>
        </label>
        <label>权重 <input v-model.number="fWeight" type="number" /></label>
        <label>排序等级 <input v-model.number="fRankLevel" type="number" min="1" /></label>
        <label>发布时间 <input v-model="fPublishedAt" type="datetime-local" /></label>
        <label>下线时间 <input v-model="fOfflineAt" type="datetime-local" /></label>
        <label>内容类型 <input v-model="fContentType" placeholder="article/video/image/link/text" /></label>
        <label>来源链接 <input v-model="fSourceUrl" placeholder="https://..." /></label>
        <label class="full">
          上传图片
          <input type="file" accept="image/jpeg,image/png,image/gif,image/webp" @change="onPickCover" />
        </label>
        <div v-if="fCoverUrl" class="full preview">
          <img :src="fCoverUrl" alt="cover" />
        </div>
        <label class="chk-inline full">
          <input v-model="fPublished" type="checkbox" />
          <span>发布后访客可见</span>
        </label>
        <label class="chk-inline full">
          <input v-model="fIsPinned" type="checkbox" />
          <span>置顶</span>
        </label>
        <label class="chk-inline full">
          <input v-model="fIsFeatured" type="checkbox" />
          <span>精选</span>
        </label>
        <p v-if="formErr" class="error full">{{ formErr }}</p>
      </div>
      <template #footer>
        <button type="button" class="secondary" @click="formOpen = false">取消</button>
        <button type="button" :disabled="saving" @click="saveForm">{{ saving ? "保存中…" : "保存" }}</button>
      </template>
    </BaseModal>

    <ConfirmDialog
      :open="delOpen"
      title="删除文章"
      :message="delMsg"
      @close="delOpen = false"
      @confirm="confirmDelete"
    />
  </div>
</template>

<style scoped>
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem 1rem;
  min-width: 0;
}
.form-grid label:not(.chk-inline) {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
}
.form-grid .full {
  grid-column: 1 / -1;
}
.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  min-width: 0;
}
.form-field-label {
  font-size: 0.9rem;
  color: var(--muted);
}
.tags-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: stretch;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--emoji-bar-bg);
  min-width: 0;
}
.tag-chk {
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  gap: 0.4rem;
  margin: 0;
  padding: 0.35rem 0.55rem;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  font-size: 0.8125rem;
  line-height: 1.3;
  cursor: pointer;
  max-width: 100%;
}
.tag-chk:has(input:checked) {
  border-color: color-mix(in srgb, var(--accent) 55%, var(--border));
  background: color-mix(in srgb, var(--accent) 14%, var(--surface));
}
.tag-chip-name {
  font-weight: 600;
  color: var(--text);
  max-width: 7rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tag-chip-slug {
  font-size: 0.72rem;
  color: var(--muted);
  font-family: ui-monospace, monospace;
  max-width: 5.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rte-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
  max-width: 100%;
  margin-bottom: 0.35rem;
}
.rte-label {
  font-size: 0.9rem;
  color: var(--muted);
}
.tag-pill {
  display: inline-block;
  margin: 0.15rem 0.35rem 0.15rem 0;
  padding: 0.2rem 0.55rem;
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1.35;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--accent) 40%, var(--border));
  background: color-mix(in srgb, var(--accent) 12%, var(--surface));
  color: var(--text);
  white-space: nowrap;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: middle;
}
.tags-cell {
  max-width: 14rem;
  min-width: 6rem;
  vertical-align: top;
  line-height: 1.5;
}
.tags-empty {
  color: var(--muted);
}
.admin-data-table .col-tags {
  min-width: 7rem;
}
.preview img {
  max-width: 100%;
  max-height: 180px;
  border-radius: 8px;
  border: 1px solid var(--border);
}
select {
  font: inherit;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
}
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
</style>
