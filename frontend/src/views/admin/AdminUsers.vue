<script setup>
import { ref, watch } from "vue";
import { useRouter } from "vue-router";
import AdminPaginationBar from "../../components/AdminPaginationBar.vue";
import BaseModal from "../../components/BaseModal.vue";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import {
  createUserAdmin,
  deleteUserAdmin,
  listUsersAdmin,
  updateUserAdmin,
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
const fUsername = ref("");
const fPassword = ref("");
const fActive = ref(true);
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
    let { data } = await listUsersAdmin({ skip, limit: pageSize.value });
    const maxP = Math.max(1, Math.ceil(data.total / pageSize.value) || 1);
    if (p > maxP && data.total >= 0) {
      page.value = maxP;
      p = maxP;
      ({ data } = await listUsersAdmin({
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
      router.push({ name: "admin-login", query: { redirect: "/admin/users" } });
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
  formTitle.value = "新增用户";
  fUsername.value = "";
  fPassword.value = "";
  fActive.value = true;
  formErr.value = "";
  formOpen.value = true;
}

function openEdit(r) {
  editingId.value = r.id;
  formTitle.value = "编辑用户";
  fUsername.value = r.username;
  fPassword.value = "";
  fActive.value = r.is_active;
  formErr.value = "";
  formOpen.value = true;
}

async function save() {
  formErr.value = "";
  const username = fUsername.value.trim();
  if (!username) {
    formErr.value = "请填写用户名";
    return;
  }
  saving.value = true;
  try {
    if (editingId.value == null) {
      const password = fPassword.value;
      if (!password || password.length < 6) {
        formErr.value = "新建用户密码至少 6 位";
        saving.value = false;
        return;
      }
      await createUserAdmin({ username, password, is_active: fActive.value });
    } else {
      const body = { username, is_active: fActive.value };
      if (fPassword.value.trim()) {
        body.password = fPassword.value;
      }
      await updateUserAdmin(editingId.value, body);
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
  delMsg.value = `确定删除用户「${r.username}」（id=${r.id}）？`;
  delOpen.value = true;
}

async function confirmDel() {
  if (!delRow.value) return;
  try {
    await deleteUserAdmin(delRow.value.id);
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
      <p class="admin-toolbar-desc">后台登录账号；密码仅存哈希。禁用后无法换取 JWT。</p>
      <div class="admin-toolbar-actions">
        <button type="button" @click="openCreate">新增用户</button>
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
            <th>用户名</th>
            <th>密码哈希</th>
            <th>启用</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.id }}</td>
            <td>{{ r.username }}</td>
            <td class="admin-mono admin-cell-clip-wide" :title="r.hashed_password">
              {{ r.hashed_password }}
            </td>
            <td>{{ r.is_active }}</td>
            <td class="admin-mono">{{ r.created_at }}</td>
            <td class="admin-ops">
              <button type="button" class="secondary" @click="openEdit(r)">编辑</button>
              <button type="button" class="danger" @click="askDel(r)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!rows.length" class="admin-table-empty">暂无用户。</p>
    </div>

    <BaseModal :open="formOpen" :title="formTitle" @close="formOpen = false">
      <label>用户名 <input v-model="fUsername" autocomplete="off" /></label>
      <label style="margin-top: 0.75rem">
        密码
        <input v-model="fPassword" type="password" autocomplete="new-password" :placeholder="editingId ? '不修改请留空' : '至少 6 位'" />
      </label>
      <label class="chk-inline" style="margin-top: 0.75rem">
        <input v-model="fActive" type="checkbox" />
        <span>启用该账号登录</span>
      </label>
      <p v-if="formErr" class="error" style="margin-top: 0.75rem">{{ formErr }}</p>
      <template #footer>
        <button type="button" class="secondary" @click="formOpen = false">取消</button>
        <button type="button" :disabled="saving" @click="save">{{ saving ? "保存中…" : "保存" }}</button>
      </template>
    </BaseModal>

    <ConfirmDialog :open="delOpen" title="删除用户" :message="delMsg" @close="delOpen = false" @confirm="confirmDel" />
  </div>
</template>

<style scoped>
label:not(.chk-inline) {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
}
</style>
