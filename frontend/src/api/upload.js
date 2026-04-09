/** 后台上传图片，返回相对路径 URL */
import client from "./http.js";

export function uploadImage(file) {
  const form = new FormData();
  form.append("file", file);
  return client.post("/upload/image", form);
}
