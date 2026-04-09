/** 标签后台 CRUD */
import { createAdminCrudApi } from "./adminCrud.js";

const tagsApi = createAdminCrudApi("tags");

export const listTagsAdmin = tagsApi.list;
export const getTagAdmin = tagsApi.get;
export const createTag = tagsApi.create;
export const updateTag = tagsApi.update;
export const deleteTag = tagsApi.remove;
