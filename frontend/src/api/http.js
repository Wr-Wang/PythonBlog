/**
 * Axios 单例：baseURL 指向 /api（Vite dev 代理到后端）。
 * 请求拦截器自动附带 localStorage 中的 JWT。
 * 401：清除无效 token；若当前在需登录的后台路由，则跳转登录页（登录接口本身的 401 不处理）。
 */
import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 60000,
});

/** 避免多个并行 401 重复触发 location.replace */
let authRedirectScheduled = false;

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("blog_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 后端 503/4xx 常返回 { detail: "..." }，合并到 message 便于页面统一展示
client.interceptors.response.use(
  (res) => res,
  (err) => {
    const data = err.response?.data;
    const detail = data?.detail;
    if (detail != null) {
      err.message =
        typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((x) => x.msg || x).join("; ") : JSON.stringify(detail);
    }

    const status = err.response?.status;
    const url = err.config?.url || "";
    const isLoginRequest = url.includes("/auth/login");

    if (status === 401 && !isLoginRequest && localStorage.getItem("blog_token")) {
      localStorage.removeItem("blog_token");
      window.dispatchEvent(new CustomEvent("blog-token-cleared"));
      const path = window.location.pathname;
      if (path.startsWith("/admin") && path !== "/admin/login" && !authRedirectScheduled) {
        authRedirectScheduled = true;
        const back = encodeURIComponent(path + window.location.search);
        window.location.replace(
          `/admin/login?redirect=${back}&reason=session_expired`,
        );
      }
    }

    return Promise.reject(err);
  },
);

export default client;
