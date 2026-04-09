/** 登录、登出、当前用户（JWT 由 http 拦截器带上） */
import client from "./http.js";

export function login(username, password) {
  return client.post("/auth/login", { username, password });
}

export function authLogout() {
  return client.post("/auth/logout");
}

export function authMe() {
  return client.get("/auth/me");
}
