/**
 * 前端 API 聚合出口：按领域拆分为多文件，此处统一导出。
 * 页面使用：`import { login } from "../api"`；需 axios 实例时可 `import { client } from "../api"`。
 */
export * from "./auth.js";
export * from "./categories.js";
export * from "./comments.js";
export * from "./posts.js";
export * from "./tags.js";
export * from "./upload.js";
export * from "./users.js";
export { default as client } from "./http.js";
