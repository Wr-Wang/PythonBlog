import client from "./http.js";

export function listRoles(params = {}) {
  return client.get("/admin/rbac/roles", { params });
}

export function createRole(data) {
  return client.post("/admin/rbac/roles", data);
}

export function updateRole(roleId, data) {
  return client.patch(`/admin/rbac/roles/${roleId}`, data);
}

export function listPermissions() {
  return client.get("/admin/rbac/permissions");
}

export function listMenus() {
  return client.get("/admin/rbac/menus");
}

export function createMenu(data) {
  return client.post("/admin/rbac/menus", data);
}

export function updateMenu(menuId, data) {
  return client.patch(`/admin/rbac/menus/${menuId}`, data);
}

export function bindUserRoles(userId, role_ids) {
  return client.post(`/admin/rbac/users/${userId}/bind-roles`, { role_ids });
}

export function getUserRoleBindings(userId) {
  return client.get(`/admin/rbac/users/${userId}/roles`);
}

export function bindRole(roleId, permission_ids = [], menu_ids = []) {
  return client.post(`/admin/rbac/roles/${roleId}/bind`, { permission_ids, menu_ids });
}

export function getRoleBindings(roleId) {
  return client.get(`/admin/rbac/roles/${roleId}/bindings`);
}

export function listAuditLogs(params = {}) {
  return client.get("/admin/rbac/audit-logs", { params });
}
