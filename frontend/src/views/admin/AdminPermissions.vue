<script setup>
import { onMounted, ref } from "vue";
import BaseModal from "../../components/BaseModal.vue";
import {
  bindRole,
  createMenu,
  createRole,
  getRoleBindings,
  listAuditLogs,
  listMenus,
  listPermissions,
  listRoles,
  updateMenu,
  updateRole,
} from "../../api";
import { hasPermission } from "../../utils/permissions";

const loading = ref(false);
const err = ref("");
const msg = ref("");
const tab = ref("roles"); // roles | menus

const roles = ref([]);
const menus = ref([]);
const perms = ref([]);
const audits = ref([]);

const roleFormOpen = ref(false);
const editingRole = ref(null);
const rfCode = ref("");
const rfName = ref("");
const rfScope = ref("all");
const rfActive = ref(true);
const roleSaving = ref(false);

const menuFormOpen = ref(false);
const editingMenu = ref(null);
const mfCode = ref("");
const mfName = ref("");
const mfRoute = ref("");
const mfOrder = ref(0);
const mfHidden = ref(false);
const menuSaving = ref(false);

const bindPermOpen = ref(false);
const bindMenuOpen = ref(false);
const bindRoleRow = ref(null);
const bindPermIds = ref([]);
const bindMenuIds = ref([]);
const bindSaving = ref(false);
const canViewRoles = hasPermission("admin.roles.view");
const canCreateRole = hasPermission("admin.roles.create");
const canUpdateRole = hasPermission("admin.roles.update");
const canBindPerms = hasPermission("admin.roles.bind_permissions");
const canBindMenus = hasPermission("admin.roles.bind_menus");
const canViewMenus = hasPermission("admin.menus.view");
const canCreateMenu = hasPermission("admin.menus.create");
const canUpdateMenu = hasPermission("admin.menus.update");
const canViewPerms = hasPermission("admin.permissions.view");
const canViewAudit = hasPermission("admin.audit.view");
const canReadPermList = canViewPerms || canBindPerms;
const canReadMenuList = canViewMenus || canBindMenus;

function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : v;
}

function hasId(list, id) {
  const arr = Array.isArray(list) ? list : list?.value;
  if (!Array.isArray(arr)) return false;
  const target = toNum(id);
  return arr.some((x) => toNum(x) === target);
}

function sameIdSet(a = [], b = []) {
  const sa = [...new Set(a.map((x) => toNum(x)))].sort((x, y) => Number(x) - Number(y));
  const sb = [...new Set(b.map((x) => toNum(x)))].sort((x, y) => Number(x) - Number(y));
  if (sa.length !== sb.length) return false;
  for (let i = 0; i < sa.length; i += 1) {
    if (sa[i] !== sb[i]) return false;
  }
  return true;
}

function toggleIn(listRef, id) {
  const base = Array.isArray(listRef?.value) ? listRef.value : [];
  const target = toNum(id);
  if (hasId(base, target)) {
    const next = base.filter((x) => toNum(x) !== target);
    listRef.value = next;
  } else {
    const next = [...base.map((x) => toNum(x)), target];
    listRef.value = next;
  }
}

function isPermChecked(id) {
  return hasId(bindPermIds.value, id);
}

function isMenuChecked(id) {
  return hasId(bindMenuIds.value, id);
}

function togglePerm(id) {
  toggleIn(bindPermIds, id);
}

function toggleMenu(id) {
  toggleIn(bindMenuIds, id);
}

async function load() {
  loading.value = true;
  err.value = "";
  if (!canViewRoles && !canViewMenus) {
    loading.value = false;
    err.value = "缺少权限: admin.roles.view 或 admin.menus.view";
    return;
  }
  try {
    const tasks = [];
    if (canViewRoles) tasks.push(listRoles({ skip: 0, limit: 500 }));
    if (canReadPermList) tasks.push(listPermissions());
    if (canReadMenuList) tasks.push(listMenus());
    if (canViewAudit) tasks.push(listAuditLogs({ skip: 0, limit: 20 }));
    const results = await Promise.all(tasks);
    let idx = 0;
    if (canViewRoles) roles.value = results[idx++].data.items || [];
    else roles.value = [];
    if (canReadPermList) perms.value = results[idx++].data.items || [];
    else perms.value = [];
    if (canReadMenuList) menus.value = results[idx++].data.items || [];
    else menus.value = [];
    if (canViewAudit) audits.value = results[idx++].data.items || [];
    else audits.value = [];
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

function openRoleCreate() {
  editingRole.value = null;
  rfCode.value = "";
  rfName.value = "";
  rfScope.value = "all";
  rfActive.value = true;
  roleFormOpen.value = true;
}
function openRoleEdit(r) {
  editingRole.value = r;
  rfCode.value = r.code;
  rfName.value = r.name;
  rfScope.value = r.data_scope || "all";
  rfActive.value = !!r.is_active;
  roleFormOpen.value = true;
}
async function saveRole() {
  roleSaving.value = true;
  try {
    const body = {
      code: rfCode.value.trim(),
      name: rfName.value.trim(),
      data_scope: rfScope.value,
      is_active: rfActive.value,
    };
    if (editingRole.value) await updateRole(editingRole.value.id, body);
    else await createRole(body);
    roleFormOpen.value = false;
    await load();
    msg.value = "角色保存成功";
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "角色保存失败";
  } finally {
    roleSaving.value = false;
  }
}

function openMenuCreate() {
  editingMenu.value = null;
  mfCode.value = "";
  mfName.value = "";
  mfRoute.value = "";
  mfOrder.value = 0;
  mfHidden.value = false;
  menuFormOpen.value = true;
}
function openMenuEdit(m) {
  editingMenu.value = m;
  mfCode.value = m.code;
  mfName.value = m.name;
  mfRoute.value = m.route;
  mfOrder.value = m.order_no || 0;
  mfHidden.value = !!m.hidden;
  menuFormOpen.value = true;
}
async function saveMenu() {
  menuSaving.value = true;
  try {
    const body = {
      code: mfCode.value.trim(),
      name: mfName.value.trim(),
      route: mfRoute.value.trim(),
      order_no: Number(mfOrder.value || 0),
      hidden: mfHidden.value,
    };
    if (editingMenu.value) await updateMenu(editingMenu.value.id, body);
    else await createMenu(body);
    menuFormOpen.value = false;
    await load();
    msg.value = "菜单保存成功";
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "菜单保存失败";
  } finally {
    menuSaving.value = false;
  }
}

async function openBindPerm(r) {
  msg.value = "";
  err.value = "";
  bindRoleRow.value = r;
  const { data } = await getRoleBindings(r.id);
  bindPermIds.value = (data.permission_ids || []).map((x) => toNum(x));
  bindMenuOpen.value = false;
  bindPermOpen.value = true;
}
async function openBindMenu(r) {
  msg.value = "";
  err.value = "";
  bindRoleRow.value = r;
  const { data } = await getRoleBindings(r.id);
  bindMenuIds.value = (data.menu_ids || []).map((x) => toNum(x));
  bindPermOpen.value = false;
  bindMenuOpen.value = true;
}
async function saveBindPerm() {
  if (!bindRoleRow.value) return;
  msg.value = "";
  err.value = "";
  bindSaving.value = true;
  try {
    const { data } = await getRoleBindings(bindRoleRow.value.id);
    const payload = {
      permission_ids: bindPermIds.value.map((x) => toNum(x)),
      menu_ids: (data.menu_ids || []).map((x) => toNum(x)),
    };
    console.log("[RBAC] saveBindPerm request", {
      role_id: bindRoleRow.value.id,
      payload,
    });
    const resp = await bindRole(bindRoleRow.value.id, payload.permission_ids, payload.menu_ids);
    console.log("[RBAC] saveBindPerm response", {
      role_id: bindRoleRow.value.id,
      data: resp?.data,
      status: resp?.status,
    });
    const { data: verify } = await getRoleBindings(bindRoleRow.value.id);
    if (!sameIdSet(verify.permission_ids || [], bindPermIds.value)) {
      throw new Error("权限点保存未生效，请刷新后重试");
    }
    bindPermOpen.value = false;
    await load();
    msg.value = "权限点绑定已保存";
  } catch (e) {
    console.error("[RBAC] saveBindPerm failed", {
      role_id: bindRoleRow.value?.id,
      selected_permission_ids: bindPermIds.value,
      error: e?.response?.data || e?.message || e,
    });
    msg.value = "";
    err.value = e.response?.data?.detail || e.message || "保存失败";
  } finally {
    bindSaving.value = false;
  }
}
async function saveBindMenu() {
  if (!bindRoleRow.value) return;
  msg.value = "";
  err.value = "";
  bindSaving.value = true;
  try {
    const { data } = await getRoleBindings(bindRoleRow.value.id);
    const payload = {
      permission_ids: (data.permission_ids || []).map((x) => toNum(x)),
      menu_ids: bindMenuIds.value.map((x) => toNum(x)),
    };
    console.log("[RBAC] saveBindMenu request", {
      role_id: bindRoleRow.value.id,
      payload,
    });
    const resp = await bindRole(bindRoleRow.value.id, payload.permission_ids, payload.menu_ids);
    console.log("[RBAC] saveBindMenu response", {
      role_id: bindRoleRow.value.id,
      data: resp?.data,
      status: resp?.status,
    });
    const { data: verify } = await getRoleBindings(bindRoleRow.value.id);
    if (!sameIdSet(verify.menu_ids || [], bindMenuIds.value)) {
      throw new Error("菜单绑定保存未生效，请刷新后重试");
    }
    bindMenuOpen.value = false;
    await load();
    msg.value = "菜单绑定已保存";
  } catch (e) {
    console.error("[RBAC] saveBindMenu failed", {
      role_id: bindRoleRow.value?.id,
      selected_menu_ids: bindMenuIds.value,
      error: e?.response?.data || e?.message || e,
    });
    msg.value = "";
    err.value = e.response?.data?.detail || e.message || "保存失败";
  } finally {
    bindSaving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="card">
    <h2>权限管理</h2>
    <div class="tabs">
      <button type="button" class="secondary" :class="{ active: tab === 'roles' }" @click="tab = 'roles'">
        角色管理
      </button>
      <button type="button" class="secondary" :class="{ active: tab === 'menus' }" @click="tab = 'menus'">
        菜单管理
      </button>
    </div>

    <p v-if="loading" class="meta">加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <template v-else>
      <p v-if="msg" class="meta">{{ msg }}</p>

      <div v-if="tab === 'roles'">
        <div class="admin-toolbar-actions">
          <button v-if="canCreateRole" type="button" @click="openRoleCreate">新增角色</button>
        </div>
        <table class="admin-data-table">
          <thead>
            <tr>
              <th>ID</th><th>编码</th><th>名称</th><th>数据范围</th><th>启用</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in roles" :key="r.id">
              <td>{{ r.id }}</td>
              <td>{{ r.code }}</td>
              <td>{{ r.name }}</td>
              <td>{{ r.data_scope || 'all' }}</td>
              <td>{{ r.is_active }}</td>
              <td class="admin-ops">
                <a v-if="canUpdateRole" href="#" class="op-link" @click.prevent="openRoleEdit(r)">编辑</a>
                <span v-if="canUpdateRole && (canBindPerms || canBindMenus)" class="op-sep"> | </span>
                <a v-if="canBindPerms" href="#" class="op-link" @click.prevent="openBindPerm(r)">绑定权限点</a>
                <span v-if="canBindPerms && canBindMenus" class="op-sep"> | </span>
                <a v-if="canBindMenus" href="#" class="op-link" @click.prevent="openBindMenu(r)">菜单绑定</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else>
        <div class="admin-toolbar-actions">
          <button v-if="canCreateMenu" type="button" @click="openMenuCreate">新增菜单</button>
        </div>
        <table class="admin-data-table">
          <thead>
            <tr>
              <th>ID</th><th>编码</th><th>名称</th><th>路由</th><th>排序</th><th>隐藏</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in menus" :key="m.id">
              <td>{{ m.id }}</td>
              <td>{{ m.code }}</td>
              <td>{{ m.name }}</td>
              <td>{{ m.route }}</td>
              <td>{{ m.order_no }}</td>
              <td>{{ m.hidden }}</td>
              <td class="admin-ops">
                <a v-if="canUpdateMenu" href="#" class="op-link" @click.prevent="openMenuEdit(m)">编辑</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <template v-if="canViewAudit">
        <h3 style="margin-top: 1rem">审计日志（最近20条）</h3>
        <ul>
          <li v-for="x in audits" :key="x.id">
            {{ x.created_at }} | {{ x.action }} | {{ x.target_type }}#{{ x.target_id }} | {{ x.detail || "-" }}
          </li>
        </ul>
      </template>
    </template>

    <BaseModal :open="roleFormOpen" :title="editingRole ? '编辑角色' : '新增角色'" @close="roleFormOpen = false">
      <label>编码 <input v-model="rfCode" /></label>
      <label style="margin-top: 0.75rem">名称 <input v-model="rfName" /></label>
      <label style="margin-top: 0.75rem">
        数据范围
        <select v-model="rfScope">
          <option value="all">all</option>
          <option value="self">self</option>
        </select>
      </label>
      <label class="chk-inline" style="margin-top: 0.75rem">
        <input v-model="rfActive" type="checkbox" />
        <span>启用</span>
      </label>
      <template #footer>
        <button type="button" class="secondary" @click="roleFormOpen = false">取消</button>
        <button type="button" :disabled="roleSaving" @click="saveRole">{{ roleSaving ? "保存中…" : "保存" }}</button>
      </template>
    </BaseModal>

    <BaseModal :open="menuFormOpen" :title="editingMenu ? '编辑菜单' : '新增菜单'" @close="menuFormOpen = false">
      <label>编码 <input v-model="mfCode" /></label>
      <label style="margin-top: 0.75rem">名称 <input v-model="mfName" /></label>
      <label style="margin-top: 0.75rem">路由 <input v-model="mfRoute" /></label>
      <label style="margin-top: 0.75rem">排序 <input v-model.number="mfOrder" type="number" /></label>
      <label class="chk-inline" style="margin-top: 0.75rem">
        <input v-model="mfHidden" type="checkbox" />
        <span>隐藏</span>
      </label>
      <template #footer>
        <button type="button" class="secondary" @click="menuFormOpen = false">取消</button>
        <button type="button" :disabled="menuSaving" @click="saveMenu">{{ menuSaving ? "保存中…" : "保存" }}</button>
      </template>
    </BaseModal>

    <BaseModal :open="bindPermOpen" title="给角色绑定权限点" @close="bindPermOpen = false">
      <p class="meta" v-if="bindRoleRow">角色：{{ bindRoleRow.name }}</p>
      <ul class="pick-list">
        <li v-for="p in perms" :key="'pp-' + p.id">
          <label class="chk-inline">
            <input type="checkbox" :checked="isPermChecked(p.id)" @change="togglePerm(p.id)" />
            <span>{{ p.name }}（{{ p.code }}）</span>
          </label>
        </li>
      </ul>
      <template #footer>
        <button type="button" class="secondary" @click="bindPermOpen = false">取消</button>
        <button type="button" :disabled="bindSaving" @click="saveBindPerm">{{ bindSaving ? "保存中…" : "保存" }}</button>
      </template>
    </BaseModal>

    <BaseModal :open="bindMenuOpen" title="给角色绑定菜单" @close="bindMenuOpen = false">
      <p class="meta" v-if="bindRoleRow">角色：{{ bindRoleRow.name }}</p>
      <ul class="pick-list">
        <li v-for="m in menus" :key="'mm-' + m.id">
          <label class="chk-inline">
            <input type="checkbox" :checked="isMenuChecked(m.id)" @change="toggleMenu(m.id)" />
            <span>{{ m.name }}（{{ m.route }}）</span>
          </label>
        </li>
      </ul>
      <template #footer>
        <button type="button" class="secondary" @click="bindMenuOpen = false">取消</button>
        <button type="button" :disabled="bindSaving" @click="saveBindMenu">{{ bindSaving ? "保存中…" : "保存" }}</button>
      </template>
    </BaseModal>
  </section>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.tabs .active {
  border-color: var(--accent);
}
.pick-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 320px;
  overflow: auto;
}
label:not(.chk-inline) {
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
.op-sep {
  color: var(--muted);
}
</style>
