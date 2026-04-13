<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { authLogout, authMe } from "../../api";
import { getTheme, setTheme } from "../../theme.js";

const route = useRoute();
const router = useRouter();

const pageTitle = computed(() => {
  for (let i = route.matched.length - 1; i >= 0; i--) {
    const t = route.matched[i].meta?.adminTitle;
    if (t) return t;
  }
  return "管理控制台";
});

const themePref = ref(getTheme());
const userMenuOpen = ref(false);
const profileLoading = ref(false);
const profileLoadErr = ref("");
const profile = ref(readProfileFromStorage());

const displayName = computed(() => profile.value?.username || "未登录用户");
const primaryRole = computed(() => {
  const roles = profile.value?.roles;
  return Array.isArray(roles) && roles.length ? roles[0] : "未分配角色";
});
const avatarText = computed(() => {
  const name = String(displayName.value || "").trim();
  return name ? name.slice(0, 1).toUpperCase() : "U";
});

function applyThemeFromUi() {
  setTheme(themePref.value);
}

function readProfileFromStorage() {
  try {
    const raw = localStorage.getItem("blog_profile");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

async function loadProfile() {
  profileLoading.value = true;
  profileLoadErr.value = "";
  try {
    const { data } = await authMe();
    profile.value = data || null;
    localStorage.setItem("blog_profile", JSON.stringify(data || {}));
  } catch {
    profileLoadErr.value = "用户信息加载失败，请重试";
  } finally {
    profileLoading.value = false;
  }
}

function toggleUserMenu() {
  userMenuOpen.value = !userMenuOpen.value;
}

function closeUserMenu() {
  userMenuOpen.value = false;
}

function goProfile() {
  closeUserMenu();
  router.push("/admin/users");
}

function onDocPointerDown(event) {
  const target = event?.target;
  if (!(target instanceof Element)) return;
  if (!target.closest(".top-user")) closeUserMenu();
}

const navBase = [
  { to: "/admin/home", label: "首页", sub: "工作台总览" },
  { to: "/admin/posts", label: "文章", sub: "撰写与列表" },
  { to: "/admin/categories", label: "分类", sub: "栏目与 slug" },
  { to: "/admin/tags", label: "标签", sub: "检索用标记" },
  { to: "/admin/users", label: "用户", sub: "后台账号" },
  { to: "/admin/comments", label: "评论", sub: "访客留言" },
  { to: "/admin/dashboard", label: "运营看板", sub: "数据与告警" },
  { to: "/admin/workflow", label: "流程中心", sub: "送审与发布" },
  { to: "/admin/permissions", label: "权限管理", sub: "RBAC 与审计" },
];
const allowedMenus = computed(() => {
  try {
    const raw = localStorage.getItem("blog_profile");
    const profile = raw ? JSON.parse(raw) : null;
    const menus = Array.isArray(profile?.menus) ? profile.menus : [];
    return new Set(menus);
  } catch {
    return new Set();
  }
});
const nav = computed(() => {
  const allow = allowedMenus.value;
  return navBase.filter((x) => x.to === "/admin/home" || allow.has(x.to));
});

async function logout() {
  try {
    await authLogout();
  } catch {
    /* ignore */
  }
  localStorage.removeItem("blog_token");
  localStorage.removeItem("blog_profile");
  router.push({ name: "admin-login" });
}

onMounted(() => {
  if (!profile.value?.username) {
    loadProfile();
  }
  document.addEventListener("pointerdown", onDocPointerDown);
});
onUnmounted(() => {
  document.removeEventListener("pointerdown", onDocPointerDown);
});
</script>

<template>
  <div class="admin-shell">
    <aside class="admin-side" aria-label="后台导航">
      <div class="side-brand">
        <span class="brand-mark" aria-hidden="true" />
        <div class="brand-text">
          <span class="brand-name">控制台</span>
          <span class="brand-tag">Blog</span>
        </div>
      </div>

      <nav class="side-nav">
        <router-link v-for="item in nav" :key="item.to" :to="item.to" class="nav-item">
          <span class="nav-label">{{ item.label }}</span>
          <span class="nav-sub">{{ item.sub }}</span>
        </router-link>
      </nav>

      <div class="side-footer">
        <router-link class="footer-link" to="/">返回站点</router-link>
        <button type="button" class="footer-logout" @click="logout">退出登录</button>
      </div>
    </aside>

    <div class="admin-main">
      <header class="admin-top">
        <div class="top-title-block">
          <p class="top-crumb">后台管理</p>
          <h1 class="top-page-title">{{ pageTitle }}</h1>
        </div>
        <div class="admin-top-actions">
          <label class="sr-only" for="admin-theme">外观</label>
          <select
            id="admin-theme"
            v-model="themePref"
            class="toolbar-select admin-theme-select"
            @change="applyThemeFromUi"
          >
            <option value="system">跟随系统</option>
            <option value="light">浅色</option>
            <option value="dark">深色</option>
          </select>
          <div class="top-user">
            <button
              type="button"
              class="top-user-btn"
              :aria-expanded="userMenuOpen ? 'true' : 'false'"
              :disabled="profileLoading"
              @click="toggleUserMenu"
            >
              <span class="top-user-avatar">{{ avatarText }}</span>
              <span class="top-user-meta">
                <span class="top-user-name">{{ profileLoading ? "加载中..." : displayName }}</span>
                <span class="top-user-role">{{ primaryRole }}</span>
              </span>
            </button>
            <div v-if="userMenuOpen" class="top-user-menu" role="menu" aria-label="用户菜单">
              <button type="button" class="top-user-menu-item" role="menuitem" @click="goProfile">个人信息</button>
              <button type="button" class="top-user-menu-item danger" role="menuitem" @click="logout">退出登录</button>
            </div>
          </div>
          <button
            v-if="profileLoadErr"
            type="button"
            class="secondary top-user-retry"
            title="重新加载用户信息"
            @click="loadProfile"
          >
            重试用户信息
          </button>
          <button type="button" class="top-logout secondary" @click="logout">退出</button>
        </div>
      </header>
      <div class="admin-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-shell {
  display: flex;
  min-height: 100vh;
  background: var(--bg);
}

.admin-side {
  width: 112px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 1rem 0.65rem 0.8rem;
  background: var(--admin-aside-gradient);
  border-right: 1px solid var(--border);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.2);
}

.side-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 0.35rem 0.85rem;
  margin-bottom: 0.25rem;
  border-bottom: 1px solid var(--border);
}

.brand-mark {
  width: 8px;
  height: 30px;
  border-radius: 4px;
  background: linear-gradient(180deg, var(--accent-hover) 0%, var(--accent) 100%);
  box-shadow: 0 0 20px rgba(91, 155, 213, 0.35);
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.brand-name {
  font-weight: 700;
  font-size: 0.96rem;
  letter-spacing: 0.02em;
}

.brand-tag {
  font-size: 0.66rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--muted);
}

.side-nav {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  flex: 1;
  padding-top: 0.7rem;
}

.nav-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.1rem;
  padding: 0.38rem 0.38rem 0.38rem 0.5rem;
  border-radius: 8px;
  color: var(--muted);
  text-decoration: none;
  transition: color 0.15s ease, background 0.15s ease;
}

.nav-item:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.04);
}

.nav-item.router-link-active {
  color: var(--accent-hover);
  background: rgba(91, 155, 213, 0.12);
}

.nav-item.router-link-active::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 55%;
  border-radius: 0 3px 3px 0;
  background: var(--accent);
}

.nav-label {
  font-weight: 600;
  font-size: 0.78rem;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-sub {
  display: block;
  font-size: 0.56rem;
  color: inherit;
  opacity: 0.76;
  line-height: 1.15;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.side-footer {
  margin-top: auto;
  padding-top: 0.7rem;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.footer-link {
  font-size: 0.82rem;
  padding: 0.38rem 0.5rem;
  color: var(--muted);
  border-radius: 8px;
}

.footer-link:hover {
  color: var(--accent-hover);
  background: rgba(255, 255, 255, 0.04);
}

.footer-logout {
  font: inherit;
  cursor: pointer;
  text-align: left;
  padding: 0.38rem 0.5rem;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
  font-size: 0.82rem;
}

.footer-logout:hover {
  color: var(--danger);
  background: rgba(229, 115, 115, 0.08);
}

.admin-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  width: 100%;
  overflow: visible;
}

.admin-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.5rem 1rem 1.75rem;
  border-bottom: 1px solid var(--border);
  background: var(--header-bar-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.admin-top-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.65rem;
}

.admin-theme-select {
  max-width: 8rem;
}

.top-user {
  position: relative;
}

.top-user-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 11rem;
  padding: 0.28rem 0.45rem;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--card);
  color: inherit;
  cursor: pointer;
}

.top-user-avatar {
  width: 1.6rem;
  height: 1.6rem;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  font-weight: 700;
  background: rgba(91, 155, 213, 0.15);
  color: var(--accent-hover);
}

.top-user-meta {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
}

.top-user-name,
.top-user-role {
  max-width: 7.2rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.2;
}

.top-user-name {
  font-size: 0.75rem;
  font-weight: 600;
}

.top-user-role {
  font-size: 0.62rem;
  color: var(--muted);
}

.top-user-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 0.35rem);
  min-width: 7.2rem;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.22rem;
  box-shadow: 0 10px 22px rgba(0, 0, 0, 0.22);
  z-index: 20;
}

.top-user-menu-item {
  width: 100%;
  border: none;
  background: transparent;
  color: inherit;
  text-align: left;
  font: inherit;
  font-size: 0.75rem;
  padding: 0.38rem 0.5rem;
  border-radius: 8px;
  cursor: pointer;
}

.top-user-menu-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.top-user-menu-item.danger:hover {
  color: var(--danger);
  background: rgba(229, 115, 115, 0.1);
}

.top-user-retry {
  padding: 0.35rem 0.55rem;
  white-space: nowrap;
}

.top-title-block {
  min-width: 0;
}

.top-crumb {
  margin: 0 0 0.2rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--muted);
}

.top-page-title {
  margin: 0;
  font-size: 1.65rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.15;
}

.top-logout {
  flex-shrink: 0;
}

.admin-content {
  flex: 1;
  padding: 1.5rem 1.75rem 2.5rem;
  overflow-y: auto;
  overflow-x: auto;
  min-width: 0;
}

/* 1366x768 常见后台分辨率：压缩头部与内容留白，提升首屏信息密度 */
@media (max-width: 1400px) and (max-height: 800px) {
  .admin-top {
    padding: 0.72rem 1rem 0.72rem 1.1rem;
  }
  .top-crumb {
    margin-bottom: 0.1rem;
    font-size: 0.66rem;
    letter-spacing: 0.1em;
  }
  .top-page-title {
    font-size: 1.28rem;
    line-height: 1.1;
  }
  .admin-top-actions {
    gap: 0.4rem;
  }
  .admin-theme-select {
    max-width: 6.5rem;
  }
  .top-user-btn {
    min-width: 8.6rem;
    padding: 0.22rem 0.4rem;
  }
  .top-user-name,
  .top-user-role {
    max-width: 5.8rem;
  }
  .admin-content {
    padding: 0.88rem 1rem 1.05rem;
  }
}

.admin-content :deep(.admin-page) {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow-x: visible;
}

.admin-content :deep(.admin-toolbar),
.admin-content :deep(.admin-pagination),
.admin-content :deep(.admin-table-scroll) {
  max-width: 100%;
  min-width: 0;
}

@media (max-width: 900px) {
  .admin-shell {
    flex-direction: column;
  }

  .admin-side {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
    align-items: flex-start;
    padding: 1rem;
    box-shadow: none;
    border-right: none;
    border-bottom: 1px solid var(--border);
  }

  .side-brand {
    width: 100%;
    padding-bottom: 0.85rem;
    margin-bottom: 0.75rem;
  }

  .side-nav {
    flex-direction: row;
    flex-wrap: wrap;
    flex: 1 1 auto;
    padding-top: 0;
    gap: 0.5rem;
  }

  .nav-item {
    flex: 1 1 auto;
    min-width: 6.5rem;
    padding: 0.55rem 0.75rem;
  }

  .nav-item.router-link-active::before {
    display: none;
  }

  .nav-sub {
    display: none;
  }

  .side-footer {
    flex-direction: row;
    width: 100%;
    border-top: none;
    padding-top: 0.75rem;
    margin-top: 0;
    border-top: 1px solid var(--border);
  }

  .footer-logout {
    margin-left: auto;
  }

  .top-logout {
    display: none;
  }
  .top-user-btn {
    min-width: auto;
  }
  .top-user-meta {
    display: none;
  }

  .admin-content {
    padding: 1.1rem 1rem 2rem;
  }
}
</style>
