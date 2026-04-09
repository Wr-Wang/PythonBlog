/** 评论：后台管理 + 按文章公开列表/发表 */
import client from "./http.js";

/** UTF-8 → Base64（ASCII），供 content_b64；服务端优先解码，避免 IIS/代理损坏正文 Unicode。 */
function utf8ToBase64(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}

function withContentB64(payload) {
  if (!payload || typeof payload.content !== "string") return payload;
  return { ...payload, content_b64: utf8ToBase64(payload.content) };
}

function sendComment(method, url, payload) {
  return client.request({ method, url, data: withContentB64(payload) });
}

export function listCommentsAdmin(params = {}) {
  return client.get("/comments/admin", { params });
}

export function getCommentAdmin(id) {
  return client.get(`/comments/admin/${id}`);
}

export function createCommentAdmin(data) {
  return sendComment("post", "/comments/admin", data);
}

export function updateCommentAdmin(id, data) {
  return sendComment("patch", `/comments/admin/${id}`, data);
}

export function deleteCommentAdmin(id) {
  return client.delete(`/comments/admin/${id}`);
}

export function listCommentsByPost(postId) {
  return client.get(`/comments/by-post/${postId}`);
}

export function createCommentPublic(postId, data) {
  return sendComment("post", `/comments/by-post/${postId}`, data);
}
