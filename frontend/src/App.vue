<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { authLogout } from "./api";

const route = useRoute();
const router = useRouter();

const hideHeader = computed(
  () => route.meta.hideHeader === true || route.meta.adminLayout === true,
);

const isAuthed = ref(!!localStorage.getItem("blog_token"));
watch(
  () => route.fullPath,
  () => {
    isAuthed.value = !!localStorage.getItem("blog_token");
  },
);

async function logout() {
  try {
    await authLogout();
  } catch {
    /* 仍清除本地 token */
  }
  localStorage.removeItem("blog_token");
  isAuthed.value = false;
  await router.push({ name: "home" });
}
</script>

<template>
  <div class="layout">
    <header v-if="!hideHeader" class="site-header">
      <h1><router-link to="/">个人博客</router-link></h1>
      <nav>
        <router-link to="/">首页</router-link>
        <router-link to="/admin/posts">管理</router-link>
        <button v-if="isAuthed" type="button" class="secondary" @click="logout">
          退出登录
        </button>
      </nav>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>
