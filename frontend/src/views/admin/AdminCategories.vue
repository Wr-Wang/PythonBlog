<script setup>
import { ref, watch } from "vue";
import { useRouter } from "vue-router";
import AdminPaginationBar from "../../components/AdminPaginationBar.vue";
import BaseModal from "../../components/BaseModal.vue";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import {
  createCategory,
  deleteCategory,
  listCategoriesAdmin,
  updateCategory,
} from "../../api";

const router = useRouter();
const rows = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const loading = ref(true);
const err = ref("");

const formOpen = ref(false);
const formTitle = ref("");
const editingId = ref(null);
const fName = ref("");
const fSlug = ref("");
const formErr = ref("");
const saving = ref(false);

const delOpen = ref(false);
const delRow = ref(null);
const delMsg = ref("");

async function load() {
  loading.value = true;
  err.value = "";
  try {
    let p = page.value;
    const skip = (p - 1) * pageSize.value;
    let { data } = await listCategoriesAdmin({ skip, limit: pageSize.value });
    const maxP = Math.max(1, Math.ceil(data.total / pageSize.value) || 1);
    if (p > maxP && data.total >= 0) {
      page.value = maxP;
      p = maxP;
      ({ data } = await listCategoriesAdmin({
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
      router.push({ name: "admin-login", query: { redirect: "/admin/categories" } });
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

function openCreate() {
  editingId.value = null;
  formTitle.value = "新增分类";
  fName.value = "";
  fSlug.value = "";
  formErr.value = "";
  formOpen.value = true;
}

function openEdit(r) {
  editingId.value = r.id;
  formTitle.value = "编辑分类";
  fName.value = r.name;
  fSlug.value = r.slug;
  formErr.value = "";
  formOpen.value = true;
}

async function save() {
  formErr.value = "";
  const name = fName.value.trim();
  const slug = fSlug.value.trim();
  if (!name || !slug) {
    formErr.value = "请填写名称与 slug";
    return;
  }
  saving.value = true;
  try {
    if (editingId.value == null) {
      await createCategory({ name, slug });
    } else {
      await updateCategory(editingId.value, { name, slug });
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
  delMsg.value = `确定删除分类「${r.name}」（id=${r.id}）？`;
  delOpen.value = true;
}

async function confirmDel() {
  if (!delRow.value) return;
  try {
    await deleteCategory(delRow.value.id);
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
      <p class="admin-toolbar-desc">为文章划分栏目；slug 用于 URL 与程序引用，需保持唯一。</p>
      <div class="admin-toolbar-actions">
        <button type="button" @click="openCreate">新增分类</button>
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
      <table class="admin-data-table">
        <thead>
          <tr>
            <th>编号</th>
            <th>名称</th>
            <th>URL 标识</th>
            <th>创建时间</th>
            <th>更新时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.id }}</td>
            <td>{{ r.name }}</td>
            <td>{{ r.slug }}</td>
            <td class="admin-mono">{{ r.created_at }}</td>
            <td class="admin-mono">{{ r.updated_at }}</td>
            <td class="admin-ops">
              <a href="#" class="op-link" @click.prevent="openEdit(r)">编辑</a>
              <span class="op-sep"> | </span>
              <a href="#" class="op-link danger-link" @click.prevent="askDel(r)">删除</a>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!rows.length" class="admin-table-empty">暂无分类。</p>
    </div>

    <BaseModal :open="formOpen" :title="formTitle" @close="formOpen = false">
      <label>名称 <input v-model="fName" /></label>
      <label style="margin-top: 0.75rem">slug <input v-model="fSlug" /></label>
      <p v-if="formErr" class="error" style="margin-top: 0.75rem">{{ formErr }}</p>
      <template #footer>
        <button type="button" class="secondary" @click="formOpen = false">取消</button>
        <button type="button" :disabled="saving" @click="save">{{ saving ? "保存中…" : "保存" }}</button>
      </template>
    </BaseModal>

    <ConfirmDialog :open="delOpen" title="删除分类" :message="delMsg" @close="delOpen = false" @confirm="confirmDel" />
  </div>
</template>

<style scoped>
label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
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
