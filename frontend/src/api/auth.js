/** 登录、登出、当前用户（JWT 由 http 拦截器带上） */
import client from "./http.js";

/** 获取验证码（图形/算术轮换） */
export function fetchCaptcha() {
  return client.get("/auth/captcha");
}

/**
 * @param {{ username: string, password: string, captcha_id?: string | null, captcha_answer?: string | null }} payload
 */
export function login(payload) {
  return client.post("/auth/login", {
    username: payload.username,
    password: payload.password,
    captcha_id: payload.captcha_id ?? null,
    captcha_answer: payload.captcha_answer ?? null,
  });
}

export function authLogout() {
  return client.post("/auth/logout");
}

export function authMe() {
  return client.get("/auth/me");
}
