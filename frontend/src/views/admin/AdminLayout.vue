<script setup>
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { authLogout } from "../../api";

const route = useRoute();
const router = useRouter();

const pageTitle = computed(() => {
  for (let i = route.matched.length - 1; i >= 0; i--) {
    const t = route.matched[i].meta?.adminTitle;
    if (t) return t;
  }
  return "管理控制台";
});

const nav = [
  { to: "/admin/posts", label: "文章", sub: "撰写与列表" },
  { to: "/admin/categories", label: "分类", sub: "栏目与 slug" },
  { to: "/admin/tags", label: "标签", sub: "检索用标记" },
  { to: "/admin/users", label: "用户", sub: "后台账号" },
  { to: "/admin/comments", label: "评论", sub: "访客留言" },
];

async function logout() {
  try {
    await authLogout();
  } catch {
    /* ignore */
  }
  localStorage.removeItem("blog_token");
  router.push({ name: "admin-login" });
}
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
        <button type="button" class="top-logout secondary" @click="logout">退出</button>
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
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 1.35rem 0.9rem 1rem;
  background: linear-gradient(165deg, #121922 0%, var(--surface) 48%, #151d2a 100%);
  border-right: 1px solid var(--border);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.2);
}

.side-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 0.5rem 1.25rem;
  margin-bottom: 0.25rem;
  border-bottom: 1px solid var(--border);
}

.brand-mark {
  width: 10px;
  height: 40px;
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
  font-size: 1.05rem;
  letter-spacing: 0.02em;
}

.brand-tag {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--muted);
}

.side-nav {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex: 1;
  padding-top: 1rem;
}

.nav-item {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.65rem 0.85rem 0.65rem 0.95rem;
  border-radius: 10px;
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
  font-size: 0.94rem;
}

.nav-sub {
  font-size: 0.72rem;
  color: inherit;
  opacity: 0.85;
}

.side-footer {
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.footer-link {
  font-size: 0.875rem;
  padding: 0.45rem 0.65rem;
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
  padding: 0.45rem 0.65rem;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
  font-size: 0.875rem;
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
}

.admin-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.5rem 1rem 1.75rem;
  border-bottom: 1px solid var(--border);
  background: rgba(15, 20, 25, 0.65);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
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
  overflow: auto;
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

  .admin-content {
    padding: 1.1rem 1rem 2rem;
  }
}
</style>
