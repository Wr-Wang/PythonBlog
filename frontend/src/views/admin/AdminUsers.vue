<script setup>
import { ref } from "vue";
import AdminPaginationBar from "../../components/AdminPaginationBar.vue";
import BaseModal from "../../components/BaseModal.vue";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import {
  bindUserRoles,
  createUserAdmin,
  deleteUserAdmin,
  getUserRoleBindings,
  listUsersAdmin,
  listRoles,
  updateUserAdmin,
} from "../../api";
import { useAdminListPage } from "../../composables/useAdminListPage";
import { hasPermission } from "../../utils/permissions";

// 用户新增/编辑弹窗状态。
const formOpen = ref(false);
const formTitle = ref("");
const editingId = ref(null);
const fUsername = ref("");
const fPassword = ref("");
const fActive = ref(true);
const formErr = ref("");
const saving = ref(false);

// 删除确认弹窗状态。
const delOpen = ref(false);
const delRow = ref(null);
const delMsg = ref("");
// 角色绑定弹窗状态。
const bindOpen = ref(false);
const bindUser = ref(null);
const allRoles = ref([]);
const bindRoleIds = ref([]);
const bindSaving = ref(false);
const bindErr = ref("");
// 页面级权限开关（决定按钮可见性与动作可用性）。
const canViewUsers = hasPermission("admin.users.view");
const canCreateUser = hasPermission("admin.users.create");
const canEditUser = hasPermission("admin.users.update");
const canDeleteUser = hasPermission("admin.users.delete");
const canBindRoles = hasPermission("admin.users.bind_roles");

// 注意：useAdminListPage 初始化会立即执行 load，需先初始化权限常量。
const { rows, total, page, pageSize, loading, err, load, setPage, onPageSizeChange } = useAdminListPage({
  listFn: async (params) => {
    // 无查看权限时返回空列表，避免额外请求与报错噪音。
    if (!canViewUsers) return { data: { items: [], total: 0 } };
    return listUsersAdmin(params);
  },
  redirectPath: "/admin/users",
});

function toNum(v) {
  /** 统一 ID 比较类型，避免字符串/数字混用导致勾选状态异常。 */
  const n = Number(v);
  return Number.isFinite(n) ? n : v;
}

function hasRoleId(id) {
  /** 判断某角色是否已被当前“绑定角色”弹窗选中。 */
  const t = toNum(id);
  return bindRoleIds.value.some((x) => toNum(x) === t);
}

async function loadRolesMeta() {
  /** 拉取角色元数据供绑定弹窗展示。 */
  const { data } = await listRoles({ skip: 0, limit: 500 });
  allRoles.value = data.items || [];
}

if (!canViewUsers) err.value = "缺少权限: admin.users.view";

function openCreate() {
  /** 打开新增用户弹窗并重置表单。 */
  editingId.value = null;
  formTitle.value = "新增用户";
  fUsername.value = "";
  fPassword.value = "";
  fActive.value = true;
  formErr.value = "";
  formOpen.value = true;
}

function openEdit(r) {
  /** 打开编辑用户弹窗（密码默认留空代表不改）。 */
  editingId.value = r.id;
  formTitle.value = "编辑用户";
  fUsername.value = r.username;
  fPassword.value = "";
  fActive.value = r.is_active;
  formErr.value = "";
  formOpen.value = true;
}

async function save() {
  /** 保存新增/编辑用户。 */
  formErr.value = "";
  const username = fUsername.value.trim();
  if (!username) {
    formErr.value = "请填写用户名";
    return;
  }
  saving.value = true;
  try {
    if (editingId.value == null) {
      // 新建用户强制校验最小密码长度。
      const password = fPassword.value;
      if (!password || password.length < 6) {
        formErr.value = "新建用户密码至少 6 位";
        saving.value = false;
        return;
      }
      await createUserAdmin({ username, password, is_active: fActive.value });
    } else {
      // 编辑时仅在输入新密码时才下发 password 字段。
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
  /** 打开删除确认弹窗。 */
  delRow.value = r;
  delMsg.value = `确定删除用户「${r.username}」（id=${r.id}）？`;
  delOpen.value = true;
}

async function openBindRoles(r) {
  /** 打开绑定角色弹窗并加载当前绑定结果。 */
  bindErr.value = "";
  bindUser.value = r;
  bindOpen.value = true;
  try {
    await loadRolesMeta();
    const { data } = await getUserRoleBindings(r.id);
    bindRoleIds.value = (data.role_ids || []).map((x) => toNum(x));
  } catch (e) {
    bindErr.value = e.response?.data?.detail || e.message || "加载绑定信息失败";
  }
}

function toggleBindRole(roleId) {
  /** 切换某角色在“待保存绑定集”中的状态。 */
  const target = toNum(roleId);
  if (hasRoleId(target)) {
    bindRoleIds.value = bindRoleIds.value.filter((x) => toNum(x) !== target);
  } else {
    bindRoleIds.value = [...bindRoleIds.value.map((x) => toNum(x)), target];
  }
}

async function saveBindRoles() {
  /** 提交角色绑定关系。 */
  if (!bindUser.value) return;
  bindSaving.value = true;
  bindErr.value = "";
  try {
    await bindUserRoles(bindUser.value.id, bindRoleIds.value.map((x) => toNum(x)));
    bindOpen.value = false;
  } catch (e) {
    bindErr.value = e.response?.data?.detail || e.message || "保存绑定失败";
  } finally {
    bindSaving.value = false;
  }
}

async function confirmDel() {
  /** 确认删除用户并刷新列表。 */
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
        <button v-if="canCreateUser" type="button" @click="openCreate">新增用户</button>
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
              <!-- 操作按钮按权限组合展示，避免越权入口暴露。 -->
              <a v-if="canEditUser" href="#" class="op-link" @click.prevent="openEdit(r)">编辑</a>
              <span v-if="canEditUser && (canBindRoles || canDeleteUser)" class="op-sep"> | </span>
              <a v-if="canBindRoles" href="#" class="op-link" @click.prevent="openBindRoles(r)">绑定角色</a>
              <span v-if="canBindRoles && canDeleteUser" class="op-sep"> | </span>
              <a v-if="canDeleteUser" href="#" class="op-link danger-link" @click.prevent="askDel(r)">删除</a>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!rows.length" class="admin-table-empty">暂无用户。</p>
    </div>

    <BaseModal :open="formOpen" :title="formTitle" @close="formOpen = false">
      <!-- 新增/编辑共用同一表单；编辑时密码留空表示不修改。 -->
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
    <BaseModal :open="bindOpen" title="给用户绑定角色" @close="bindOpen = false">
      <!-- 角色勾选集合本地维护，点击“保存角色绑定”统一提交。 -->
      <p class="meta" v-if="bindUser">当前用户：{{ bindUser.username }}</p>
      <p v-if="bindErr" class="error">{{ bindErr }}</p>
      <ul class="role-list">
        <li v-for="r in allRoles" :key="'b-' + r.id">
          <label class="chk-inline">
            <input
              type="checkbox"
              :checked="hasRoleId(r.id)"
              @change="toggleBindRole(r.id)"
            />
            <span>{{ r.name }}（{{ r.code }}）</span>
          </label>
        </li>
      </ul>
      <template #footer>
        <button type="button" class="secondary" @click="bindOpen = false">取消</button>
        <button type="button" :disabled="bindSaving" @click="saveBindRoles">
          {{ bindSaving ? "保存中…" : "保存角色绑定" }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
label:not(.chk-inline) {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
}
.role-list {
  list-style: none;
  margin: 0.75rem 0 0;
  padding: 0;
  max-height: 320px;
  overflow: auto;
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
