/** 分类后台 CRUD */
import { createAdminCrudApi } from "./adminCrud.js";

const categoriesApi = createAdminCrudApi("categories");

export const listCategoriesAdmin = categoriesApi.list;
export const getCategoryAdmin = categoriesApi.get;
export const createCategory = categoriesApi.create;
export const updateCategory = categoriesApi.update;
export const deleteCategory = categoriesApi.remove;
