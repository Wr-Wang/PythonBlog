/** 用户后台 CRUD */
import { createAdminCrudApi } from "./adminCrud.js";

const usersApi = createAdminCrudApi("users");

export const listUsersAdmin = usersApi.list;
export const getUserAdmin = usersApi.get;
export const createUserAdmin = usersApi.create;
export const updateUserAdmin = usersApi.update;
export const deleteUserAdmin = usersApi.remove;
