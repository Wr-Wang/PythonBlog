/**
 * 后台会话缓存层：
 * - 统一 profile 拉取，避免路由守卫与布局页重复请求 /auth/me。
 * - 提供轻量内存缓存 + 正在请求中的 Promise 复用。
 */
import { authMe } from "../api";

const PROFILE_KEY = "blog_profile";
let profileCache = null;
let inflight = null;

function readProfileFromStorage() {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeProfile(profile) {
  profileCache = profile || null;
  localStorage.setItem(PROFILE_KEY, JSON.stringify(profile || {}));
}

export function clearSessionProfile() {
  profileCache = null;
  inflight = null;
  localStorage.removeItem(PROFILE_KEY);
}

export function getCachedProfile() {
  if (profileCache) return profileCache;
  const fromStorage = readProfileFromStorage();
  if (fromStorage) profileCache = fromStorage;
  return profileCache;
}

/**
 * 拉取当前用户 profile。
 * @param {{ force?: boolean }} opts
 */
export async function getOrFetchProfile(opts = {}) {
  const force = !!opts.force;
  if (!force) {
    const cached = getCachedProfile();
    if (cached?.username) return cached;
  }
  if (!force && inflight) return inflight;
  inflight = authMe()
    .then(({ data }) => {
      const profile = data || null;
      writeProfile(profile);
      return profile;
    })
    .finally(() => {
      inflight = null;
    });
  return inflight;
}

