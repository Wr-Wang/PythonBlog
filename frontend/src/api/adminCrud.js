/** 后台通用 CRUD API 工厂 */
import client from "./http.js";

export function createAdminCrudApi(resource) {
  const base = `/${resource}/admin`;
  return {
    list(params = {}) {
      return client.get(base, { params });
    },
    get(id) {
      return client.get(`${base}/${id}`);
    },
    create(data) {
      return client.post(base, data);
    },
    update(id, data) {
      return client.patch(`${base}/${id}`, data);
    },
    remove(id) {
      return client.delete(`${base}/${id}`);
    },
  };
}
