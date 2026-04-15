<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchCaptcha, login } from "../api";

const route = useRoute();
const router = useRouter();

const username = ref("admin");
const password = ref("");
const err = ref("");
const loading = ref(false);

const captchaRequired = ref(false);
const captchaId = ref("");
const captchaAnswer = ref("");
const captchaType = ref(""); // image | math
const captchaQuestion = ref("");
const imageB64 = ref("");
const captchaLoading = ref(false);

const sessionHint = computed(() =>
  // 登录页可感知守卫传入原因，给出更明确提示。
  route.query.reason === "session_expired"
    ? "登录已过期或无效，请重新登录。"
    : "",
);

function detailMessage(e) {
  /** 统一提取后端错误消息（兼容字符串/对象 detail）。 */
  const d = e.response?.data?.detail;
  if (d && typeof d === "object" && !Array.isArray(d)) {
    return d.message || d.msg || "登录失败";
  }
  if (typeof d === "string") return d;
  return e.message || "登录失败";
}

function detailCaptchaRequired(e) {
  /** 判断本次登录失败是否需要验证码。 */
  const d = e.response?.data?.detail;
  return !!(d && typeof d === "object" && d.captcha_required);
}

async function loadCaptcha() {
  /** 拉取验证码，支持 image/math 两种形态。 */
  captchaAnswer.value = "";
  captchaLoading.value = true;
  try {
    const { data } = await fetchCaptcha();
    captchaId.value = data.captcha_id || "";
    captchaType.value = data.captcha_type || "";
    if (data.captcha_type === "image") {
      // 图片验证码：前端展示 base64 PNG。
      imageB64.value = data.image_b64 || "";
      captchaQuestion.value = "";
    } else {
      // 算术验证码：展示题面文本。
      imageB64.value = "";
      captchaQuestion.value = data.question || "";
    }
  } catch (ce) {
    err.value = ce.response?.data?.detail || ce.message || "验证码加载失败";
  } finally {
    captchaLoading.value = false;
  }
}

async function submit() {
  /** 登录提交：按需附带验证码字段。 */
  err.value = "";
  if (captchaRequired.value) {
    const a = captchaAnswer.value.trim();
    if (!a) {
      err.value = "请填写验证码";
      return;
    }
  }
  loading.value = true;
  try {
    const payload = {
      username: username.value,
      password: password.value,
    };
    if (captchaRequired.value) {
      // 当后端要求验证码时，必须携带 captcha_id + captcha_answer。
      payload.captcha_id = captchaId.value;
      payload.captcha_answer = captchaAnswer.value;
    }
    const { data } = await login(payload);
    localStorage.setItem("blog_token", data.access_token);
    captchaRequired.value = false;
    const redirect = route.query.redirect || "/admin/home";
    await router.replace(typeof redirect === "string" ? redirect : "/admin/home");
  } catch (e) {
    err.value = detailMessage(e);
    const need = detailCaptchaRequired(e);
    if (need) captchaRequired.value = true;
    // 要求验证码或已在验证码模式下时，自动刷新一题。
    if (captchaRequired.value) await loadCaptcha();
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
        <div v-if="captchaRequired" class="captcha-block">
          <p class="captcha-hint">请输入验证码（形态轮换）</p>
          <div v-if="captchaLoading" class="meta">验证码加载中…</div>
          <template v-else>
            <div v-if="captchaType === 'image' && imageB64" class="captcha-img-wrap">
              <img class="captcha-img" :src="`data:image/png;base64,${imageB64}`" alt="验证码" />
            </div>
            <p v-else-if="captchaType === 'math'" class="captcha-math">{{ captchaQuestion }}</p>
            <div class="captcha-row">
              <input
                v-model="captchaAnswer"
                type="text"
                class="captcha-input"
                placeholder="验证码"
                autocomplete="off"
                autocapitalize="off"
              />
              <button type="button" class="secondary captcha-refresh" @click="loadCaptcha">换一张</button>
            </div>
          </template>
        </div>
        <p v-if="sessionHint" class="session-hint">{{ sessionHint }}</p>
        <p v-if="err" class="error">{{ err }}</p>
        <button type="submit" :disabled="loading || (captchaRequired && captchaLoading)">
          {{ loading ? "登录中…" : "登录" }}
        </button>
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
.captcha-block {
  margin: 0.75rem 0 0;
  padding: 0.75rem 0.85rem;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.15);
}
.captcha-hint {
  margin: 0 0 0.5rem;
  font-size: 0.85rem;
  color: var(--muted);
}
.captcha-img-wrap {
  margin-bottom: 0.5rem;
}
.captcha-img {
  display: block;
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  border: 1px solid var(--border);
}
.captcha-math {
  margin: 0 0 0.5rem;
  font-size: 1.15rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.captcha-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.captcha-input {
  flex: 1;
  min-width: 0;
}
.captcha-refresh {
  flex-shrink: 0;
  white-space: nowrap;
}
</style>
