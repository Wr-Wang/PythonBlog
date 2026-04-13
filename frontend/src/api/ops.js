import client from "./http.js";

export function getDashboardSummary() {
  return client.get("/admin/ops/dashboard");
}

export function transitionPost(postId, to_status) {
  return client.post(`/admin/ops/posts/${postId}/transition`, null, {
    params: { to_status },
  });
}

export function getDashboardTrends(params = {}) {
  return client.get("/admin/ops/trends", { params });
}

export function exportDashboardTrends(format = "csv", params = {}) {
  return client.get("/admin/ops/export", {
    params: { format, ...params },
    responseType: "blob",
  });
}

export function listFeatureFlags() {
  return client.get("/admin/ops/feature-flags");
}

export function updateFeatureFlag(flagId, payload) {
  return client.post(`/admin/ops/feature-flags/${flagId}`, null, { params: payload });
}

export function getModerationLists() {
  return client.get("/admin/ops/moderation");
}

export function addSensitiveWord(word) {
  return client.post("/admin/ops/moderation/sensitive", null, { params: { word } });
}

export function addBlacklistWord(word) {
  return client.post("/admin/ops/moderation/blacklist", null, { params: { word } });
}

export function getSearchOps() {
  return client.get("/admin/ops/search-ops");
}

export function addSearchSynonym(src, dst) {
  return client.post("/admin/ops/search-ops/synonyms", null, { params: { src, dst } });
}
