<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { authLogout } from "./api";
import { getFontSize, getTheme, setFontSize, setTheme } from "./theme.js";

const route = useRoute();
const router = useRouter();

const hideHeader = computed(
  () => route.meta.hideHeader === true || route.meta.adminLayout === true,
);

const isAuthed = ref(!!localStorage.getItem("blog_token"));

const themePref = ref(getTheme());
const fontSizePref = ref(getFontSize());

function applyThemeFromUi() {
  setTheme(themePref.value);
}

function applyFontFromUi() {
  setFontSize(fontSizePref.value);
}

watch(
  () => route.fullPath,
  () => {
    isAuthed.value = !!localStorage.getItem("blog_token");
  },
);

function onTokenCleared() {
  isAuthed.value = false;
}

onMounted(() => {
  window.addEventListener("blog-token-cleared", onTokenCleared);
});
onUnmounted(() => {
  window.removeEventListener("blog-token-cleared", onTokenCleared);
});

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
        <router-link to="/search">搜索</router-link>
        <router-link to="/admin/home">管理</router-link>
        <div class="header-tools">
          <label class="sr-only" for="pub-theme">外观</label>
          <select
            id="pub-theme"
            v-model="themePref"
            class="toolbar-select"
            @change="applyThemeFromUi"
          >
            <option value="system">跟随系统</option>
            <option value="light">浅色</option>
            <option value="dark">深色</option>
          </select>
          <label class="sr-only" for="pub-font">字号</label>
          <select
            id="pub-font"
            v-model="fontSizePref"
            class="toolbar-select"
            @change="applyFontFromUi"
          >
            <option value="sm">小</option>
            <option value="md">中</option>
            <option value="lg">大</option>
          </select>
        </div>
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
