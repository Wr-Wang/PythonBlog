function readProfile() {
  try {
    return JSON.parse(localStorage.getItem("blog_profile") || "{}");
  } catch {
    return {};
  }
}

export function getPermissionCodes() {
  const profile = readProfile();
  return Array.isArray(profile.permissions) ? profile.permissions : [];
}

export function hasPermission(code) {
  const perms = getPermissionCodes();
  if (perms.includes("admin.super") || perms.includes(code)) return true;
  // 旧权限码兼容：兼容历史角色配置（rbac.* / post.workflow / audit.view）
  const legacyAliases = {
    "admin.roles.view": ["rbac.view"],
    "admin.permissions.view": ["rbac.view"],
    "admin.menus.view": ["rbac.view"],
    "admin.roles.create": ["rbac.manage"],
    "admin.roles.update": ["rbac.manage"],
    "admin.roles.bind_permissions": ["rbac.manage"],
    "admin.roles.bind_menus": ["rbac.manage"],
    "admin.menus.create": ["rbac.manage"],
    "admin.menus.update": ["rbac.manage"],
    "admin.users.bind_roles": ["rbac.manage"],
    "admin.audit.view": ["audit.view"],
    "admin.posts.publish.now": ["post.workflow"],
    "admin.posts.offline.now": ["post.workflow"],
  };
  const aliases = legacyAliases[code] || [];
  return aliases.some((x) => perms.includes(x));
}
