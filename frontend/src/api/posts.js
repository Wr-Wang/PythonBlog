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

export function favoritePost(postId, user_key) {
  return client.post(`/posts/${postId}/favorite`, { user_key });
}

export function unfavoritePost(postId, user_key) {
  return client.delete(`/posts/${postId}/favorite`, { params: { user_key } });
}

export function likePost(postId, user_key) {
  return client.post(`/posts/${postId}/like`, { user_key });
}

export function unlikePost(postId, user_key) {
  return client.delete(`/posts/${postId}/like`, { params: { user_key } });
}

export function sharePost(postId, channel = "link", user_key = null) {
  return client.post(`/posts/${postId}/share`, { channel, user_key });
}

export function reportPost(postId, payload) {
  return client.post(`/posts/${postId}/report`, payload);
}

export function trackPostView(postId, payload) {
  return client.post(`/posts/${postId}/view`, payload);
}

export function getPostInteractionStats(postId) {
  return client.get(`/posts/${postId}/interaction-stats`);
}

export function getPostViewMetrics(postId) {
  return client.get(`/posts/${postId}/view-metrics`);
}
