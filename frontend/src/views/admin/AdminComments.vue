<script setup>
import { ref, watch } from "vue";
import { useRouter } from "vue-router";
import AdminPaginationBar from "../../components/AdminPaginationBar.vue";
import BaseModal from "../../components/BaseModal.vue";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import {
  adminListPosts,
  createCommentAdmin,
  deleteCommentAdmin,
  listCommentsAdmin,
  updateCommentAdmin,
} from "../../api";
import { COMMENT_EMOJIS, insertEmojiAtCursor } from "../../utils/commentEmoji";

const router = useRouter();
const rows = ref([]);
const posts = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const postsLoaded = ref(false);
const loading = ref(true);
const err = ref("");

const formOpen = ref(false);
const formTitle = ref("");
const mode = ref("create"); // create | edit | reply
const editingId = ref(null);
const fPostId = ref("");
const fParentId = ref("");
const fAuthor = ref("");
const fContent = ref("");
const formErr = ref("");
const saving = ref(false);
const lockPost = ref(false);

const delOpen = ref(false);
const delRow = ref(null);
const delMsg = ref("");

async function loadPosts() {
  const { data } = await adminListPosts({ skip: 0, limit: 500 });
  posts.value = data.items ?? data;
  postsLoaded.value = true;
}

async function load() {
  loading.value = true;
  err.value = "";
  try {
    if (!postsLoaded.value) await loadPosts();
    let p = page.value;
    const skip = (p - 1) * pageSize.value;
    let { data } = await listCommentsAdmin({ skip, limit: pageSize.value });
    const maxP = Math.max(1, Math.ceil(data.total / pageSize.value) || 1);
    if (p > maxP && data.total >= 0) {
      page.value = maxP;
      p = maxP;
      ({ data } = await listCommentsAdmin({
        skip: (p - 1) * pageSize.value,
        limit: pageSize.value,
      }));
    }
    rows.value = data.items ?? data;
    total.value = data.total ?? 0;
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载失败";
    if (e.response?.status === 401) {
      localStorage.removeItem("blog_token");
      router.push({ name: "admin-login", query: { redirect: "/admin/comments" } });
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

/** 默认昵称为当前所选文章的作者（博主登录名），无作者时为空。 */
function nicknameDefaultForPost(postIdStr) {
  const id = Number(postIdStr);
  if (!Number.isFinite(id)) return "";
  const p = posts.value.find((x) => x.id === id);
  return (p && p.author_name) ? String(p.author_name) : "";
}

function openCreate() {
  mode.value = "create";
  editingId.value = null;
  formTitle.value = "新增评论";
  fPostId.value = posts.value[0] ? String(posts.value[0].id) : "";
  fParentId.value = "";
  fAuthor.value = nicknameDefaultForPost(fPostId.value);
  fContent.value = "";
  formErr.value = "";
  lockPost.value = false;
  formOpen.value = true;
}

function openEdit(r) {
  mode.value = "edit";
  editingId.value = r.id;
  formTitle.value = "编辑评论";
  fPostId.value = String(r.post_id);
  fParentId.value = r.parent_id != null ? String(r.parent_id) : "";
  fAuthor.value = r.author_name;
  fContent.value = r.content;
  formErr.value = "";
  lockPost.value = true;
  formOpen.value = true;
}

function openReply(r) {
  mode.value = "reply";
  editingId.value = null;
  formTitle.value = `回复作者：${r.author_name}`;
  fPostId.value = String(r.post_id);
  fParentId.value = String(r.id);
  fAuthor.value = "作者";
  fContent.value = "";
  formErr.value = "";
  lockPost.value = true;
  formOpen.value = true;
}

async function save() {
  formErr.value = "";
  const author_name = fAuthor.value.trim();
  const content = fContent.value.trim();
  if (!author_name || !content) {
    formErr.value = "请填写昵称与内容";
    return;
  }
  saving.value = true;
  try {
    if (mode.value === "edit") {
      await updateCommentAdmin(editingId.value, { author_name, content });
    } else {
      const post_id = Number(fPostId.value);
      if (!Number.isFinite(post_id)) {
        formErr.value = "请选择文章";
        saving.value = false;
        return;
      }
      let parent_id = null;
      if (fParentId.value !== "") {
        const p = Number(fParentId.value);
        parent_id = Number.isFinite(p) ? p : null;
      }
      await createCommentAdmin({ post_id, parent_id, author_name, content });
    }
    formOpen.value = false;
    await load();
  } catch (e) {
    formErr.value = e.response?.data?.detail || e.message || "保存失败";
  } finally {
    saving.value = false;
  }
}

function askDel(r) {
  delRow.value = r;
  delMsg.value = `确定删除评论 id=${r.id}？其回复若存在可能被一并删除（级联）。`;
  delOpen.value = true;
}

function insertEmoji(ch) {
  insertEmojiAtCursor("ac-ct", fContent, ch);
}

watch([fPostId, formOpen, mode], () => {
  if (!formOpen.value || mode.value !== "create") return;
  fAuthor.value = nicknameDefaultForPost(fPostId.value);
});

async function setStatus(r, status) {
  try {
    await updateCommentAdmin(r.id, { status });
    await load();
  } catch (e) {
    alert(e.response?.data?.detail || e.message || "更新失败");
  }
}

async function confirmDel() {
  if (!delRow.value) return;
  try {
    await deleteCommentAdmin(delRow.value.id);
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
      <p class="admin-toolbar-desc">查看与维护全站评论，可代发回复或修正违规内容。</p>
      <div class="admin-toolbar-actions">
        <button type="button" @click="openCreate">新增评论</button>
      </div>
    </div>
    <AdminPaginationBar
      v-if="!loading && !err && total > 0"
      :total="total"
      :page="page"
      :page-size="pageSize"
      @update:page="setPage"
      @page-size-change="onPageSizeChange"
    />
    <p v-if="loading" class="admin-loading">加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <div v-else class="admin-table-scroll">
      <table class="admin-data-table">
        <thead>
          <tr>
            <th>编号</th>
            <th>文章编号</th>
            <th>文章标题</th>
            <th>作者昵称</th>
            <th>内容</th>
            <th>创建时间</th>
            <th>审核状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.id }}</td>
            <td>{{ r.post_id }}</td>
            <td class="admin-cell-clip">{{ r.post_title }}</td>
            <td class="comment-text">{{ r.author_name }}</td>
            <td class="admin-cell-clip comment-text">{{ r.content }}</td>
            <td class="admin-mono">{{ r.created_at }}</td>
            <td class="admin-mono">{{ r.status || "approved" }}</td>
            <td class="admin-ops">
              <button
                v-if="r.status === 'pending'"
                type="button"
                class="secondary"
                @click="setStatus(r, 'approved')"
              >
                通过
              </button>
              <button
                v-if="r.status === 'pending'"
                type="button"
                class="secondary"
                @click="setStatus(r, 'rejected')"
              >
                拒绝
              </button>
              <button type="button" class="secondary" @click="openReply(r)">回复</button>
              <button type="button" class="secondary" @click="openEdit(r)">编辑</button>
              <button type="button" class="danger" @click="askDel(r)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!rows.length" class="admin-table-empty">暂无评论。</p>
    </div>

    <BaseModal :open="formOpen" :title="formTitle" wide @close="formOpen = false">
      <label v-if="!lockPost">
        文章
        <select v-model="fPostId">
          <option v-for="p in posts" :key="p.id" :value="String(p.id)">
            {{ p.id }} — {{ p.title }}
          </option>
        </select>
      </label>
      <p v-else class="meta">post_id: {{ fPostId }}（本表单锁定）</p>
      <label style="margin-top: 0.75rem">
        昵称
        <input
          v-model="fAuthor"
          placeholder="新增评论为文章作者；回复评论默认为「作者」，可改"
        />
      </label>
      <label style="margin-top: 0.75rem" for="ac-ct">内容</label>
      <div class="emoji-bar" role="toolbar" aria-label="插入表情">
        <button
          v-for="(em, i) in COMMENT_EMOJIS"
          :key="i"
          type="button"
          class="emoji-btn"
          :title="'插入 ' + em"
          @click="insertEmoji(em)"
        >
          {{ em }}
        </button>
      </div>
      <textarea id="ac-ct" v-model="fContent" class="comment-content-input" rows="5" />
      <p v-if="formErr" class="error" style="margin-top: 0.75rem">{{ formErr }}</p>
      <template #footer>
        <button type="button" class="secondary" @click="formOpen = false">取消</button>
        <button type="button" :disabled="saving" @click="save">{{ saving ? "保存中…" : "保存" }}</button>
      </template>
    </BaseModal>

    <ConfirmDialog :open="delOpen" title="删除评论" :message="delMsg" @close="delOpen = false" @confirm="confirmDel" />
  </div>
</template>

<style scoped>
label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
}
select {
  font: inherit;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
}
.emoji-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.35rem;
  margin-bottom: 0.5rem;
  padding: 0.45rem 0.5rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: rgba(0, 0, 0, 0.12);
  font-family: var(--font-sans, "Segoe UI", system-ui, sans-serif, "Segoe UI Emoji", "Apple Color Emoji",
    "Noto Color Emoji", emoji);
}
button.emoji-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2rem;
  min-height: 2rem;
  padding: 0.1rem 0.25rem;
  font-size: 1.25rem;
  line-height: 1;
  font-weight: 400;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text);
  cursor: pointer;
  transition: background 0.12s ease, border-color 0.12s ease;
}
button.emoji-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--border);
  color: var(--text);
}
.comment-content-input {
  font-family: var(--font-sans, "Segoe UI", system-ui, sans-serif, "Segoe UI Emoji", "Apple Color Emoji",
    "Noto Color Emoji", emoji);
  line-height: 1.5;
  width: 100%;
  box-sizing: border-box;
  font: inherit;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
}
.comment-text {
  font-family: var(--font-sans, "Segoe UI", system-ui, sans-serif, "Segoe UI Emoji", "Apple Color Emoji",
    "Noto Color Emoji", emoji);
}
</style>
