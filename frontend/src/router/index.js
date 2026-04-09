import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import PostView from "../views/PostView.vue";
import AdminLogin from "../views/AdminLogin.vue";
import AdminLayout from "../views/admin/AdminLayout.vue";
import AdminPostsPage from "../views/admin/AdminPostsPage.vue";
import AdminCategories from "../views/admin/AdminCategories.vue";
import AdminTags from "../views/admin/AdminTags.vue";
import AdminUsers from "../views/admin/AdminUsers.vue";
import AdminComments from "../views/admin/AdminComments.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
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
      ],
    },
  ],
});

router.beforeEach((to) => {
  const token = localStorage.getItem("blog_token");
  if (to.meta.requiresAuth && !token) {
    return { name: "admin-login", query: { redirect: to.fullPath } };
  }
});

export default router;
