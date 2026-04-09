/**
 * Axios 单例：baseURL 指向 /api（Vite dev 代理到后端）。
 * 请求拦截器自动附带 localStorage 中的 JWT。
 */
import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 60000,
});

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
    return Promise.reject(err);
  },
);

export default client;
