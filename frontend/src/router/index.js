import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import PostView from "../views/PostView.vue";
import SearchView from "../views/SearchView.vue";
import ColumnsView from "../views/ColumnsView.vue";
import ColumnDetailView from "../views/ColumnDetailView.vue";
import HotView from "../views/HotView.vue";
import DiscoverView from "../views/DiscoverView.vue";
import AdminLogin from "../views/AdminLogin.vue";
import AdminLayout from "../views/admin/AdminLayout.vue";
import AdminPostsPage from "../views/admin/AdminPostsPage.vue";
import AdminCategories from "../views/admin/AdminCategories.vue";
import AdminColumns from "../views/admin/AdminColumns.vue";
import AdminTags from "../views/admin/AdminTags.vue";
import AdminUsers from "../views/admin/AdminUsers.vue";
import AdminComments from "../views/admin/AdminComments.vue";
import AdminDashboard from "../views/admin/AdminDashboard.vue";
import AdminWorkflow from "../views/admin/AdminWorkflow.vue";
import AdminPermissions from "../views/admin/AdminPermissions.vue";
import AdminHome from "../views/admin/AdminHome.vue";
import { clearSessionProfile, getOrFetchProfile } from "../utils/authSession";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/search", name: "search", component: SearchView },
    { path: "/columns", name: "columns", component: ColumnsView },
    { path: "/column/:slug", name: "column-detail", component: ColumnDetailView, props: true },
    { path: "/hot", name: "hot", component: HotView },
    { path: "/discover", name: "discover", component: DiscoverView },
    { path: "/post/:slug", name: "post", component: PostView, props: true },
    {
      path: "/admin/login",
      name: "admin-login",
      component: AdminLogin,
      meta: { hideHeader: true },
    },
    {
      path: "/admin",
      component: AdminLayout,
      meta: { requiresAuth: true, adminLayout: true },
      children: [
        { path: "", redirect: "/admin/home" },
        {
          path: "home",
          name: "admin-home",
          meta: { adminTitle: "后台首页" },
          component: AdminHome,
        },
        {
          path: "posts",
          name: "admin-posts",
          meta: { adminTitle: "文章管理", requiredMenu: "/admin/posts" },
          component: AdminPostsPage,
        },
        {
          path: "columns",
          name: "admin-columns",
          meta: { adminTitle: "专栏管理", requiredMenu: "/admin/columns" },
          component: AdminColumns,
        },
        {
          path: "categories",
          name: "admin-categories",
          meta: { adminTitle: "分类管理", requiredMenu: "/admin/categories" },
          component: AdminCategories,
        },
        {
          path: "tags",
          name: "admin-tags",
          meta: { adminTitle: "标签管理", requiredMenu: "/admin/tags" },
          component: AdminTags,
        },
        {
          path: "users",
          name: "admin-users",
          meta: { adminTitle: "用户管理", requiredMenu: "/admin/users" },
          component: AdminUsers,
        },
        {
          path: "comments",
          name: "admin-comments",
          meta: { adminTitle: "评论管理", requiredMenu: "/admin/comments" },
          component: AdminComments,
        },
        {
          path: "dashboard",
          name: "admin-dashboard",
          meta: { adminTitle: "运营看板", requiredMenu: "/admin/dashboard" },
          component: AdminDashboard,
        },
        {
          path: "workflow",
          name: "admin-workflow",
          meta: { adminTitle: "流程中心", requiredMenu: "/admin/workflow" },
          component: AdminWorkflow,
        },
        {
          path: "permissions",
          name: "admin-permissions",
          meta: { adminTitle: "权限管理", requiredMenu: "/admin/permissions" },
          component: AdminPermissions,
        },
      ],
    },
  ],
});

router.beforeEach(async (to) => {
  // 1) 后台受保护路由：无 token 直接跳登录。
  const token = localStorage.getItem("blog_token");
  if (to.meta.requiresAuth && !token) {
    return { name: "admin-login", query: { redirect: to.fullPath } };
  }
  if (to.path.startsWith("/admin") && to.name !== "admin-login") {
    try {
      // 走统一会话缓存层，避免守卫与布局页重复请求 /auth/me。
      const data = await getOrFetchProfile();
      const required = to.meta?.requiredMenu;
      const menus = Array.isArray(data?.menus) ? data.menus : [];
      // 2) 菜单级权限校验：无菜单授权则回后台首页。
      if (required && !menus.includes(required)) {
        return { name: "admin-home" };
      }
    } catch {
      // 3) 会话失效：清理本地状态并带原因跳登录。
      localStorage.removeItem("blog_token");
      clearSessionProfile();
      return { name: "admin-login", query: { reason: "session_expired", redirect: to.fullPath } };
    }
  }
});

export default router;
