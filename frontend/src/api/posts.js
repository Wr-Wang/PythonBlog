/** 文章：访客列表/详情、后台 CRUD */
import client from "./http.js";

export function getPosts(params = {}) {
  return client.get("/posts", { params });
}

/** 站内搜索（已发布文章，标题/摘要，SRCH-01） */
export function searchPosts(params = {}) {
  return client.get("/posts/search", { params });
}

export function getPostBySlug(slug) {
  return client.get(`/posts/by-slug/${encodeURIComponent(slug)}`);
}

export function adminListPosts(params = {}) {
  return client.get("/posts/admin", { params });
}

export function adminGetPost(id) {
  return client.get(`/posts/admin/${id}`);
}

export function createPost(data) {
  return client.post("/posts", data);
}

export function updatePost(id, data) {
  return client.patch(`/posts/${id}`, data);
}

export function deletePost(id) {
  return client.delete(`/posts/${id}`);
}
