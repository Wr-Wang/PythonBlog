<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import BaseModal from "../../components/BaseModal.vue";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import {
  adminListPosts,
  createPost,
  deletePost,
  listCategoriesAdmin,
  listTagsAdmin,
  updatePost,
  uploadImage,
} from "../../api";

const router = useRouter();
const rows = ref([]);
const categories = ref([]);
const tags = ref([]);
const loading = ref(true);
const err = ref("");

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
const formErr = ref("");
const saving = ref(false);

const delOpen = ref(false);
const delTarget = ref(null);
const delMsg = ref("");

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
  categories.value = c.data;
  tags.value = t.data;
}

async function load() {
  loading.value = true;
  err.value = "";
  try {
    await loadMeta();
    const { data } = await adminListPosts({ limit: 500 });
    rows.value = data;
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

onMounted(load);

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
  formErr.value = "";
  formOpen.value = true;
}

function openEdit(row) {
  editingId.value = row.id;
  formTitle.value = "编辑文章";
  fTitle.value = row.title;
  fSlug.value = row.slug;
  fExcerpt.value = row.excerpt || "";
  fContent.value = row.content;
  fPublished.value = row.published;
  fCategoryId.value = row.category_id != null ? String(row.category_id) : "";
  fTagIds.value = [...(row.tag_ids || [])];
  fCoverUrl.value = row.cover_image_url || "";
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
  };
  if (!body.title || !body.slug || !body.content) {
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

function fmtTags(ids) {
  if (!ids?.length) return "—";
  return ids.join(", ");
}
</script>

<template>
  <div class="admin-page">
    <div class="admin-toolbar">
      <p class="admin-toolbar-desc">撰写与编辑正文、分类、标签及封面；访客仅可见已发布文章。</p>
      <div class="admin-toolbar-actions">
        <button type="button" @click="openCreate">新增文章</button>
      </div>
    </div>
    <p v-if="loading" class="admin-loading">加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <div v-else class="admin-table-scroll">
      <table class="admin-data-table">
        <thead>
          <tr>
            <th>id</th>
            <th>title</th>
            <th>slug</th>
            <th>excerpt</th>
            <th>published</th>
            <th>cover_image_url</th>
            <th>created_at</th>
            <th>updated_at</th>
            <th>author_id</th>
            <th>category_id</th>
            <th>category_name</th>
            <th>tag_ids</th>
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
            <td class="admin-cell-clip admin-mono">{{ r.cover_image_url || "—" }}</td>
            <td class="admin-mono">{{ r.created_at }}</td>
            <td class="admin-mono">{{ r.updated_at }}</td>
            <td>{{ r.author_id ?? "—" }}</td>
            <td>{{ r.category_id ?? "—" }}</td>
            <td>{{ r.category_name || "—" }}</td>
            <td class="admin-mono">{{ fmtTags(r.tag_ids) }}</td>
            <td class="admin-ops">
              <button type="button" class="secondary" @click="openEdit(r)">编辑</button>
              <button type="button" class="danger" @click="askDelete(r)">删除</button>
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
        <label class="full">
          正文
          <textarea v-model="fContent" rows="10" />
        </label>
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
          <div class="tags-grid" role="group" :aria-label="'标签（多选）'">
            <label v-for="t in tags" :key="t.id" class="tag-chk">
              <input type="checkbox" :checked="tagChecked(t.id)" @change="toggleTag(t.id)" />
              <span class="tag-chk-text" :title="`${t.id} ${t.name}`">{{ t.id }} {{ t.name }}</span>
            </label>
          </div>
        </div>
        <label class="full">封面图 URL <input v-model="fCoverUrl" placeholder="/uploads/xxx.jpg" /></label>
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
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(11.5rem, 1fr));
  gap: 0.35rem 0.65rem;
  align-items: center;
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.12);
  min-width: 0;
}
.tag-chk {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.45rem;
  margin: 0;
  min-width: 0;
  min-height: 1.75rem;
  font-size: 0.875rem;
  line-height: 1.35;
  cursor: pointer;
}
.tag-chk-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
</style>
