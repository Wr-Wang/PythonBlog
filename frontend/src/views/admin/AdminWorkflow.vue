<script setup>
import { ref } from "vue";
import { adminListPosts, transitionPost } from "../../api";

const loading = ref(false);
const err = ref("");
const rows = ref([]);

async function load() {
  loading.value = true;
  err.value = "";
  try {
    const { data } = await adminListPosts({ skip: 0, limit: 200 });
    rows.value = data.items || data || [];
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

async function move(post, toStatus) {
  try {
    await transitionPost(post.id, toStatus);
    await load();
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "流转失败";
  }
}

load();
</script>

<template>
  <section class="card">
    <h2>文章流程中心</h2>
    <p v-if="loading" class="meta">加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <table v-else class="tbl">
      <thead>
        <tr>
          <th>ID</th>
          <th>标题</th>
          <th>状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in rows" :key="p.id">
          <td>{{ p.id }}</td>
          <td>{{ p.title }}</td>
          <td>{{ p.review_status || (p.published ? "approved" : "draft") }}</td>
          <td>
            <a href="#" class="op-link" @click.prevent="move(p, 'pending')">送审</a>
            <span class="op-sep"> | </span>
            <a href="#" class="op-link" @click.prevent="move(p, 'approved')">通过</a>
            <span class="op-sep"> | </span>
            <a href="#" class="op-link" @click.prevent="move(p, 'rejected')">驳回</a>
            <span class="op-sep"> | </span>
            <a href="#" class="op-link" @click.prevent="move(p, 'offline')">下线</a>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.op-link {
  color: var(--accent);
  text-decoration: none;
  cursor: pointer;
}
.op-link:hover {
  text-decoration: underline;
}
.op-sep {
  color: var(--muted);
}
</style>
