import client from "./http.js";

export function listFollowedAuthors(user_key) {
  return client.get("/social/follows/authors", { params: { user_key } });
}

export function followAuthor(user_key, author_id) {
  return client.post("/social/follows/authors", { user_key, author_id });
}

export function unfollowAuthor(user_key, author_id) {
  return client.post("/social/follows/authors/unfollow", { user_key, author_id });
}
