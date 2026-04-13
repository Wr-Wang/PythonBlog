import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import PostView from "../views/PostView.vue";
import SearchView from "../views/SearchView.vue";
import AdminLogin from "../views/AdminLogin.vue";
import AdminLayout from "../views/admin/AdminLayout.vue";
import AdminPostsPage from "../views/admin/AdminPostsPage.vue";
import AdminCategories from "../views/admin/AdminCategories.vue";
import AdminTags from "../views/admin/AdminTags.vue";
import AdminUsers from "../views/admin/AdminUsers.vue";
import AdminComments from "../views/admin/AdminComments.vue";
import AdminDashboard from "../views/admin/AdminDashboard.vue";
import AdminWorkflow from "../views/admin/AdminWorkflow.vue";
import AdminPermissions from "../views/admin/AdminPermissions.vue";
import { authMe } from "../api";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/search", name: "search", component: SearchView },
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
        { path: "", redirect: "/admin/posts" },
        {
          path: "posts",
          name: "admin-posts",
          meta: { adminTitle: "文章管理" },
          component: AdminPostsPage,
        },
        {
          path: "categories",
          name: "admin-categories",
          meta: { adminTitle: "分类管理" },
          component: AdminCategories,
        },
        {
          path: "tags",
          name: "admin-tags",
          meta: { adminTitle: "标签管理" },
          component: AdminTags,
        },
        {
          path: "users",
          name: "admin-users",
          meta: { adminTitle: "用户管理" },
          component: AdminUsers,
        },
        {
          path: "comments",
          name: "admin-comments",
          meta: { adminTitle: "评论管理" },
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
  const token = localStorage.getItem("blog_token");
  if (to.meta.requiresAuth && !token) {
    return { name: "admin-login", query: { redirect: to.fullPath } };
  }
  if (to.path.startsWith("/admin") && to.name !== "admin-login") {
    try {
      const { data } = await authMe();
      localStorage.setItem("blog_profile", JSON.stringify(data || {}));
      const required = to.meta?.requiredMenu;
      if (required && Array.isArray(data?.menus) && data.menus.length > 0 && !data.menus.includes(required)) {
        return { name: "admin-posts" };
      }
    } catch {
      localStorage.removeItem("blog_token");
      localStorage.removeItem("blog_profile");
      return { name: "admin-login", query: { reason: "session_expired", redirect: to.fullPath } };
    }
  }
});

export default router;
