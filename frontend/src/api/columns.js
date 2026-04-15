import client from "./http.js";

export function listColumnsAdmin(params = {}) {
  return client.get("/columns/admin", { params });
}

export function listPublicColumns(params = {}) {
  return client.get("/columns", { params });
}

export function getPublicColumnBySlug(slug) {
  return client.get(`/columns/by-slug/${encodeURIComponent(slug)}`);
}

export function createColumn(payload) {
  return client.post("/columns/admin", payload);
}

export function updateColumn(id, payload) {
  return client.patch(`/columns/admin/${id}`, payload);
}

export function deleteColumn(id) {
  return client.delete(`/columns/admin/${id}`);
}
