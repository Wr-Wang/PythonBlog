<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { marked } from "marked";
import CommentItem from "../components/CommentItem.vue";
import {
  createCommentPublic,
  getPostBySlug,
  listCommentsByPost,
} from "../api";
import { COMMENT_EMOJIS, insertEmojiAtCursor } from "../utils/commentEmoji";

const props = defineProps({
  slug: { type: String, default: "" },
});

const route = useRoute();
const slug = computed(() => props.slug || route.params.slug);

const post = ref(null);
const loading = ref(true);
const err = ref("");

const comments = ref([]);
const cLoading = ref(false);
const cErr = ref("");
const replyTo = ref(null);
const cAuthor = ref("");
const cBody = ref("");
const cSubmitting = ref(false);
const cFormErr = ref("");

/** 访客展示作者名：随机生成，可手动修改 */
function randomGuestName() {
  const n = Math.floor(1000 + Math.random() * 9000);
  return `访客_${n}`;
}

function insertEmoji(ch) {
  insertEmojiAtCursor("ct", cBody, ch);
}

async function loadPost() {
  loading.value = true;
  err.value = "";
  post.value = null;
  comments.value = [];
  try {
    const { data } = await getPostBySlug(slug.value);
    post.value = data;
    cAuthor.value = randomGuestName();
    await loadComments(data.id);
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

async function loadComments(postId) {
  cLoading.value = true;
  cErr.value = "";
  try {
    const { data } = await listCommentsByPost(postId);
    comments.value = data;
  } catch (e) {
    cErr.value = e.response?.data?.detail || e.message || "评论加载失败";
  } finally {
    cLoading.value = false;
  }
}

const html = computed(() => {
  if (!post.value?.content) return "";
  return marked.parse(post.value.content, { async: false });
});

function nestComments(flat) {
  const map = new Map();
  flat.forEach((c) => map.set(c.id, { ...c, children: [] }));
  const roots = [];
  flat.forEach((c) => {
    const node = map.get(c.id);
    if (c.parent_id != null && map.has(c.parent_id)) {
      map.get(c.parent_id).children.push(node);
    } else {
      roots.push(node);
    }
  });
  return roots;
}

const tree = computed(() => nestComments(comments.value));

async function startReply(c) {
  replyTo.value = c;
  cFormErr.value = "";
  await nextTick();
  const el = document.getElementById("comment-form");
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  const ta = document.getElementById("ct");
  if (ta) {
    ta.focus();
  }
}

function cancelReply() {
  replyTo.value = null;
  cFormErr.value = "";
}

async function submitComment() {
  if (!post.value) return;
  cFormErr.value = "";
  const content = cBody.value.trim();
  if (!content) {
    cFormErr.value = "请填写评论内容";
    return;
  }
  let author_name = cAuthor.value.trim();
  if (!author_name) {
    author_name = randomGuestName();
    cAuthor.value = author_name;
  }
  cSubmitting.value = true;
  try {
    await createCommentPublic(post.value.id, {
      author_name,
      content,
      parent_id: replyTo.value ? replyTo.value.id : null,
    });
    cAuthor.value = randomGuestName();
    cBody.value = "";
    replyTo.value = null;
    await loadComments(post.value.id);
  } catch (e) {
    cFormErr.value = e.response?.data?.detail || e.message || "发表失败";
  } finally {
    cSubmitting.value = false;
  }
}

function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("zh-CN");
}

onMounted(loadPost);
watch(slug, loadPost);
</script>

<template>
  <div class="container">
    <p v-if="loading">加载中…</p>
    <p v-else-if="err" class="error">{{ err }}</p>
    <article v-else-if="post">
      <img
        v-if="post.cover_image_url"
        class="cover"
        :src="post.cover_image_url"
        :alt="post.title"
      />
      <h1>{{ post.title }}</h1>
      <p class="meta">{{ formatDate(post.created_at) }}</p>
      <div class="prose" v-html="html"></div>

      <section class="comments card">
        <h2 id="comment-form" class="comments-form-title">发表评论</h2>
        <ul class="comments-form-steps">
          <li>
            <strong>新评论</strong>：「作者」已随机填好（可改）；写好内容后点「发表评论」。
          </li>
          <li>
            <strong>回复某人</strong>：在下方「全部评论」里点该条旁的「回复」，表单会提示正在回复哪位作者，再填写并发送（楼中楼）。
          </li>
          <li>
            <strong>表情</strong>：内容框下方可点笑脸等图标插入到光标处；也可用系统输入法输入更多表情。
          </li>
        </ul>

        <div class="composer">
          <p v-if="replyTo" class="meta">
            回复作者：{{ replyTo.author_name }}
            <button type="button" class="secondary small" @click="cancelReply">取消</button>
          </p>
          <div class="form-row form-row-inline">
            <label for="cn">作者</label>
            <div class="author-wrap">
              <input id="cn" v-model="cAuthor" placeholder="随机已填，可改；留空提交时也会随机" />
              <button type="button" class="secondary small" @click="cAuthor = randomGuestName()">
                换一换
              </button>
            </div>
          </div>
          <div class="form-row">
            <label for="ct">内容</label>
            <div class="emoji-bar" role="toolbar" aria-label="插入表情">
              <button
                v-for="(em, i) in COMMENT_EMOJIS"
                :key="i"
                type="button"
                class="emoji-btn"
                :title="'插入 ' + em"
                @click="insertEmoji(em)"
              >
                {{ em }}
              </button>
            </div>
            <textarea
              id="ct"
              v-model="cBody"
              class="comment-content-input"
              rows="4"
              placeholder="想说点什么…"
            />
          </div>
          <p v-if="cFormErr" class="error">{{ cFormErr }}</p>
          <button type="button" :disabled="cSubmitting" @click="submitComment">
            {{ cSubmitting ? "发送中…" : replyTo ? "发表回复" : "发表评论" }}
          </button>
        </div>

        <h3 class="comments-list-title">全部评论</h3>
        <p v-if="cLoading" class="meta">评论加载中…</p>
        <p v-else-if="cErr" class="error">{{ cErr }}</p>
        <ul v-else class="thread">
          <CommentItem v-for="node in tree" :key="node.id" :node="node" @reply="startReply" />
        </ul>
        <p v-if="!cLoading && !comments.length" class="meta empty-hint">暂无评论，在上方表单留言即可。</p>
      </section>
    </article>
  </div>
</template>

<style scoped>
.cover {
  width: 100%;
  max-height: 360px;
  object-fit: cover;
  border-radius: 12px;
  margin-bottom: 1rem;
  border: 1px solid var(--border);
}
.comments {
  margin-top: 2rem;
  padding: 1.25rem;
}
.comments-form-title {
  margin: 0 0 0.35rem;
  font-size: 1.2rem;
}
.comments-form-steps {
  margin: 0 0 1rem;
  padding-left: 1.1rem;
  font-size: 0.875rem;
  color: var(--muted);
  line-height: 1.55;
}
.comments-form-steps li {
  margin-bottom: 0.35rem;
}
.comments-form-steps strong {
  color: var(--text);
}
.comments-list-title {
  margin: 1.5rem 0 0.75rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--border);
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text);
}
.empty-hint {
  margin-top: 0.5rem;
}
.thread {
  list-style: none;
  margin: 0;
  padding: 0;
}
.composer {
  margin-top: 0;
  padding-top: 0;
}
.form-row {
  margin-bottom: 0.75rem;
}
.form-row-inline label {
  display: block;
  margin-bottom: 0.35rem;
}
.author-wrap {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}
.author-wrap input {
  flex: 1;
  min-width: 10rem;
}
.emoji-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.35rem;
  margin-bottom: 0.5rem;
  padding: 0.45rem 0.5rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: rgba(0, 0, 0, 0.12);
  font-family: var(--font-sans, "Segoe UI", system-ui, sans-serif, "Segoe UI Emoji", "Apple Color Emoji",
    "Noto Color Emoji", emoji);
}
button.emoji-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2rem;
  min-height: 2rem;
  padding: 0.1rem 0.25rem;
  font-size: 1.25rem;
  line-height: 1;
  font-weight: 400;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text);
  cursor: pointer;
  transition: background 0.12s ease, border-color 0.12s ease;
}
button.emoji-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--border);
  color: var(--text);
}
.comment-content-input {
  font-family: var(--font-sans, "Segoe UI", system-ui, sans-serif, "Segoe UI Emoji", "Apple Color Emoji",
    "Noto Color Emoji", emoji);
  line-height: 1.5;
}
</style>
