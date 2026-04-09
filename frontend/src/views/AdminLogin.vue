<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { login } from "../api";

const route = useRoute();
const router = useRouter();

const username = ref("admin");
const password = ref("");
const err = ref("");
const loading = ref(false);

const sessionHint = computed(() =>
  route.query.reason === "session_expired"
    ? "登录已过期或无效，请重新登录。"
    : "",
);

async function submit() {
  err.value = "";
  loading.value = true;
  try {
    const { data } = await login(username.value, password.value);
    localStorage.setItem("blog_token", data.access_token);
    const redirect = route.query.redirect || "/admin/posts";
    await router.replace(typeof redirect === "string" ? redirect : "/admin/posts");
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card card">
      <p class="login-eyebrow">Blog Admin</p>
      <h1 class="login-title">后台登录</h1>
      <p class="login-sub">使用管理员账号进入控制台</p>
      <form @submit.prevent="submit">
        <div class="form-row">
          <label for="u">用户名</label>
          <input id="u" v-model="username" autocomplete="username" required />
        </div>
        <div class="form-row">
          <label for="p">密码</label>
          <input
            id="p"
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
          />
        </div>
        <p v-if="sessionHint" class="session-hint">{{ sessionHint }}</p>
        <p v-if="err" class="error">{{ err }}</p>
        <button type="submit" :disabled="loading">{{ loading ? "登录中…" : "登录" }}</button>
      </form>
      <p class="meta" style="margin-top: 1.5rem">
        <router-link to="/">返回首页</router-link>
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background:
    radial-gradient(ellipse 80% 60% at 50% -20%, rgba(91, 155, 213, 0.22), transparent),
    radial-gradient(ellipse 60% 50% at 100% 100%, rgba(91, 155, 213, 0.08), transparent),
    var(--bg);
}
.login-card {
  width: 100%;
  max-width: 420px;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.35);
  border: 1px solid var(--border);
}
.session-hint {
  margin: 0 0 0.75rem;
  padding: 0.65rem 0.85rem;
  font-size: 0.9rem;
  color: var(--text-muted, #94a3b8);
  background: rgba(91, 155, 213, 0.12);
  border: 1px solid rgba(91, 155, 213, 0.35);
  border-radius: 8px;
}
.login-eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--accent);
}
.login-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.login-sub {
  margin: 0.35rem 0 1.25rem;
  font-size: 0.875rem;
  color: var(--muted);
}
</style>
