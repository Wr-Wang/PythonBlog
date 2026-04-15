<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { authLogout } from "./api";
import { getFontSize, getTheme, setFontSize, setTheme } from "./theme.js";

const route = useRoute();
const router = useRouter();

const hideHeader = computed(
  // 管理后台与显式 hideHeader 页面不展示公共站点头部。
  () => route.meta.hideHeader === true || route.meta.adminLayout === true,
);

const isAuthed = ref(!!localStorage.getItem("blog_token"));

const themePref = ref(getTheme());
const fontSizePref = ref(getFontSize());

function applyThemeFromUi() {
  /** 应用站点主题偏好（system/light/dark）。 */
  setTheme(themePref.value);
}

function applyFontFromUi() {
  /** 应用站点字号偏好（sm/md/lg）。 */
  setFontSize(fontSizePref.value);
}

watch(
  () => route.fullPath,
  () => {
    // 路由切换时同步登录态，兼容登录页/后台页间跳转。
    isAuthed.value = !!localStorage.getItem("blog_token");
  },
);

function onTokenCleared() {
  /** 处理全局 token 清理事件（例如会话失效）。 */
  isAuthed.value = false;
}

onMounted(() => {
  // 监听会话清理事件，确保头部按钮状态即时更新。
  window.addEventListener("blog-token-cleared", onTokenCleared);
});
onUnmounted(() => {
  // 组件销毁时移除监听，避免重复绑定。
  window.removeEventListener("blog-token-cleared", onTokenCleared);
});

async function logout() {
  /** 退出登录：优先请求服务端，再清理本地 token 并回首页。 */
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
      <h1><router-link to="/">博客</router-link></h1>
      <nav>
        <router-link to="/">首页</router-link>
        <router-link to="/discover">发现</router-link>
        <router-link to="/columns">专栏</router-link>
        <router-link to="/hot">热榜</router-link>
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
