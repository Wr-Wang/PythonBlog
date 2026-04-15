<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import CommentItem from "../components/CommentItem.vue";
import {
  createCommentPublic,
  favoritePost,
  followAuthor,
  getPostBySlug,
  getPostInteractionStats,
  likePost,
  listCommentsByPost,
  listFollowedAuthors,
  reportPost,
  sharePost,
  trackPostView,
  unfollowAuthor,
  unfavoritePost,
  unlikePost,
} from "../api";
import { COMMENT_EMOJIS, insertEmojiAtCursor } from "../utils/commentEmoji";
import { sanitizePostBodyHtml } from "../utils/postBodyRender";
import { estimateReadingMinutes } from "../utils/readingTime";

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
const commentSuccess = ref("");
const interactionStats = ref({
  favorite_count: 0,
  like_count: 0,
  view_count: 0,
  share_count: 0,
  report_count: 0,
});
const hasLiked = ref(false);
const hasFavorited = ref(false);
const reportReason = ref("低质内容");
const shareChannel = ref("link");
const sharePanelOpen = ref(false);
const interactionMsg = ref("");
const followedAuthorIds = ref([]);
const commentsSort = ref("hot");
const shareChannelLabel = {
  link: "复制链接",
  wechat: "微信",
  weibo: "微博",
  qq: "QQ",
};
const shareOptions = [
  { value: "link", label: "复制链接", icon: "L" },
  { value: "wechat", label: "微信", icon: "W" },
  { value: "weibo", label: "微博", icon: "B" },
  { value: "qq", label: "QQ", icon: "Q" },
];

function userKey() {
  const k = "blog_guest_key";
  let v = localStorage.getItem(k);
  if (!v) {
    v = `g_${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(k, v);
  }
  return v;
}

async function syncFollowedAuthors() {
  try {
    const { data } = await listFollowedAuthors(userKey());
    followedAuthorIds.value = Array.isArray(data?.items) ? data.items.map((x) => Number(x)) : [];
  } catch {
    followedAuthorIds.value = [];
  }
}

const siteBase = (
  import.meta.env.VITE_PUBLIC_SITE_URL || ""
).replace(/\/$/, "") ||
  (typeof window !== "undefined" ? window.location.origin : "");

function absoluteUrl(u) {
  if (!u) return "";
  if (u.startsWith("http")) return u;
  return siteBase + (u.startsWith("/") ? u : `/${u}`);
}

function setMetaProperty(prop, content) {
  let el = document.querySelector(`meta[property="${prop}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute("property", prop);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
}

function removeMetaProperty(prop) {
  document.querySelector(`meta[property="${prop}"]`)?.remove();
}

function clearJsonLd() {
  document.getElementById("blog-post-jsonld")?.remove();
}

function applyArticleSeo(p) {
  if (!p) return;
  document.title = `${p.title} | 博客`;
  let metaD = document.querySelector('meta[name="description"]');
  if (!metaD) {
    metaD = document.createElement("meta");
    metaD.setAttribute("name", "description");
    document.head.appendChild(metaD);
  }
  metaD.setAttribute("content", p.excerpt || p.title);
  let link = document.querySelector('link[rel="canonical"]');
  if (!link) {
    link = document.createElement("link");
    link.setAttribute("rel", "canonical");
    document.head.appendChild(link);
  }
  const pageUrl = `${siteBase}/post/${p.slug}`;
  link.setAttribute("href", pageUrl);
  setMetaProperty("og:title", p.title);
  setMetaProperty("og:description", p.excerpt || "");
  setMetaProperty("og:url", pageUrl);
  setMetaProperty("og:type", "article");
  if (p.cover_image_url) {
    setMetaProperty("og:image", absoluteUrl(p.cover_image_url));
  } else {
    removeMetaProperty("og:image");
  }
  clearJsonLd();
  const script = document.createElement("script");
  script.id = "blog-post-jsonld";
  script.type = "application/ld+json";
  script.textContent = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: p.title,
    description: p.excerpt || undefined,
    datePublished: p.created_at,
    dateModified: p.updated_at,
    author: { "@type": "Organization", name: "博客" },
    image: p.cover_image_url ? [absoluteUrl(p.cover_image_url)] : undefined,
    mainEntityOfPage: { "@type": "WebPage", "@id": pageUrl },
  });
  document.head.appendChild(script);
}

function resetSeo() {
  document.title = "博客";
  clearJsonLd();
}

watch(
  post,
  (p) => {
    if (p) applyArticleSeo(p);
    else resetSeo();
  },
  { immediate: true },
);

const GUEST_AUTHOR_MAX = 8;

const _pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

/** 个性化访客昵称：预设 + 模板随机，语气自然、长度 ≤8 字 */
const NICK_SNACK = [
  "抹茶拿铁",
  "半糖去冰",
  "芋泥波波",
  "布丁不加糖",
  "柠檬气泡水",
  "草莓大福",
  "蓝莓夜航",
  "芒果糯米饭",
  "提拉米苏",
  "橘里橘气",
  "全糖警告",
  "少冰正常糖",
];
const NICK_LIFE = [
  "摸鱼小能手",
  "周末补觉党",
  "早睡又失败",
  "夜猫子本猫",
  "佛系阅读中",
  "躺平观赏席",
  "路过的风",
  "潜水员二号",
  "安静看文",
  "好奇心玩家",
  "码字慢半拍",
  "追剧干饭人",
];
const NICK_SCENE = [
  "晚风邮差",
  "星星收藏癖",
  "云边散步",
  "林间雾",
  "海边拾星",
  "北岛来信",
  "南风不入怀",
  "白昼梦游",
  "墨色三分白",
  "远山如黛",
  "窗台多肉",
  "雨声白噪音",
];
const NICK_FUN = [
  "读者甲",
  "路人乙",
  "故事外的人",
  "楼上一只喵",
  "键盘上飞",
  "屏幕反光",
  "Wifi满格",
  "无名火柴",
  "路过点个赞",
  "追更在前排",
];

function randomGuestName() {
  const roll = Math.random();
  let s;
  if (roll < 0.28) {
    s = _pick(NICK_SNACK);
  } else if (roll < 0.52) {
    s = _pick(NICK_LIFE);
  } else if (roll < 0.76) {
    s = _pick(NICK_SCENE);
  } else if (roll < 0.9) {
    s = _pick(NICK_FUN);
  } else if (roll < 0.96) {
    const p = _pick(["小", "阿", "老"]);
    const q = _pick(["七", "九", "豆", "米", "鹿", "鲸", "鸥", "熊", "喵"]);
    s = p + q;
  } else {
    const adj = _pick(["快乐", "安静", "好奇", "元气", "佛系", "慢热"]);
    const noun = _pick(["读者", "旅人", "追更人", "干饭人", "夜猫"]);
    s = adj + noun;
  }
  if (s.length > GUEST_AUTHOR_MAX) {
    s = s.slice(0, GUEST_AUTHOR_MAX);
  }
  return s;
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
    const key = userKey();
    await trackPostView(data.id, {
      user_key: key,
      duration_sec: 0,
      completed: false,
    });
    const st = await getPostInteractionStats(data.id);
    interactionStats.value = st.data || interactionStats.value;
    await syncFollowedAuthors();
    await loadComments(data.id);
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || "加载失败";
  } finally {
    loading.value = false;
  }
}

const isFollowingAuthor = computed(() => {
  const aid = Number(post.value?.author_id || 0);
  return aid > 0 && followedAuthorIds.value.includes(aid);
});

async function toggleFollowAuthor() {
  const aid = Number(post.value?.author_id || 0);
  if (!aid) return;
  try {
    if (isFollowingAuthor.value) {
      await unfollowAuthor(userKey(), aid);
      interactionMsg.value = "已取消关注作者";
    } else {
      await followAuthor(userKey(), aid);
      interactionMsg.value = "已关注作者";
    }
    await syncFollowedAuthors();
  } catch (e) {
    interactionMsg.value = e.response?.data?.detail || e.message || "关注操作失败";
  }
}

async function onLike() {
  if (!post.value) return;
  try {
    const key = userKey();
    if (hasLiked.value) {
      const { data } = await unlikePost(post.value.id, key);
      interactionStats.value.like_count = data.like_count ?? interactionStats.value.like_count;
      hasLiked.value = false;
    } else {
      const { data } = await likePost(post.value.id, key);
      interactionStats.value.like_count = data.like_count ?? interactionStats.value.like_count;
      hasLiked.value = true;
    }
  } catch (e) {
    interactionMsg.value = e.response?.data?.detail || e.message || "操作失败";
  }
}

async function onFavorite() {
  if (!post.value) return;
  try {
    const key = userKey();
    if (hasFavorited.value) {
      const { data } = await unfavoritePost(post.value.id, key);
      interactionStats.value.favorite_count = data.favorite_count ?? interactionStats.value.favorite_count;
      hasFavorited.value = false;
    } else {
      const { data } = await favoritePost(post.value.id, key);
      interactionStats.value.favorite_count = data.favorite_count ?? interactionStats.value.favorite_count;
      hasFavorited.value = true;
    }
  } catch (e) {
    interactionMsg.value = e.response?.data?.detail || e.message || "操作失败";
  }
}

async function onShare() {
  if (!post.value) return;
  try {
    const channel = shareChannel.value || "link";
    const { data } = await sharePost(post.value.id, channel, userKey());
    interactionStats.value.share_count = data.share_count ?? interactionStats.value.share_count;
    interactionMsg.value = `已记录转发到：${shareChannelLabel[channel] || channel}`;
    sharePanelOpen.value = false;
  } catch (e) {
    interactionMsg.value = e.response?.data?.detail || e.message || "操作失败";
  }
}

function toggleSharePanel() {
  sharePanelOpen.value = !sharePanelOpen.value;
}

async function onReport() {
  if (!post.value) return;
  try {
    await reportPost(post.value.id, { reason: reportReason.value, user_key: userKey() });
    interactionMsg.value = "举报已提交";
  } catch (e) {
    interactionMsg.value = e.response?.data?.detail || e.message || "提交失败";
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

const html = computed(() => sanitizePostBodyHtml(post.value?.content || ""));
const tocItems = computed(() => {
  if (typeof window === "undefined" || !html.value) return [];
  const doc = new window.DOMParser().parseFromString(html.value, "text/html");
  const hs = [...doc.querySelectorAll("h1,h2,h3")];
  return hs.map((h, idx) => ({
    id: h.id || `sec-${idx + 1}`,
    level: Number(h.tagName.slice(1)),
    text: (h.textContent || "").trim() || `段落 ${idx + 1}`,
  }));
});
const renderedHtml = computed(() => {
  if (typeof window === "undefined" || !html.value) return html.value;
  const doc = new window.DOMParser().parseFromString(html.value, "text/html");
  [...doc.querySelectorAll("h1,h2,h3")].forEach((h, idx) => {
    if (!h.id) h.id = `sec-${idx + 1}`;
  });
  return doc.body.innerHTML;
});

const readingMinutes = computed(() =>
  post.value?.content ? estimateReadingMinutes(post.value.content) : 1,
);

const progressPct = ref(0);
function updateScrollProgress() {
  const el = document.documentElement;
  const scrollable = el.scrollHeight - el.clientHeight;
  progressPct.value =
    scrollable <= 0 ? 100 : Math.min(100, Math.max(0, (el.scrollTop / scrollable) * 100));
}

watch([post, loading], () => {
  nextTick(() => updateScrollProgress());
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
  const byNewest = (a, b) => {
    const ta = new Date(a.created_at || 0).getTime();
    const tb = new Date(b.created_at || 0).getTime();
    if (tb !== ta) return tb - ta;
    return Number(b.id || 0) - Number(a.id || 0);
  };
  roots.sort(byNewest);
  map.forEach((node) => {
    if (Array.isArray(node.children) && node.children.length > 1) {
      node.children.sort(byNewest);
    }
  });
  return roots;
}

const tree = computed(() => nestComments(comments.value));
const displayedTree = computed(() => {
  const roots = [...tree.value];
  const newestSort = (a, b) => {
    const ta = new Date(a.created_at || 0).getTime();
    const tb = new Date(b.created_at || 0).getTime();
    return tb - ta;
  };
  const hotSort = (a, b) =>
    Number(b.children?.length || 0) - Number(a.children?.length || 0) || newestSort(a, b);
  roots.sort(commentsSort.value === "newest" ? newestSort : hotSort);
  return roots;
});

function jumpToToc(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

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
  let author_name = cAuthor.value.trim().slice(0, GUEST_AUTHOR_MAX);
  if (!author_name) {
    author_name = randomGuestName();
    cAuthor.value = author_name;
  }
  cSubmitting.value = true;
  commentSuccess.value = "";
  try {
    await createCommentPublic(post.value.id, {
      author_name,
      content,
      parent_id: replyTo.value ? replyTo.value.id : null,
    });
    commentSuccess.value = "评论发表成功，已显示在下方最新评论。";
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

onMounted(() => {
  window.addEventListener("scroll", updateScrollProgress, { passive: true });
  updateScrollProgress();
  loadPost();
});

onUnmounted(() => {
  if (post.value) {
    trackPostView(post.value.id, {
      user_key: userKey(),
      duration_sec: Math.floor((performance.now?.() || 0) / 1000),
      completed: progressPct.value >= 90,
    }).catch(() => {});
  }
  resetSeo();
  window.removeEventListener("scroll", updateScrollProgress);
});

watch(slug, loadPost);
</script>

<template>
  <div class="container post-layout">
    <div v-if="post" class="read-progress-track" aria-hidden="true">
      <div class="read-progress-bar" :style="{ width: progressPct + '%' }" />
    </div>
    <div v-if="loading" class="post-skeleton" aria-busy="true" aria-label="加载中">
      <div class="skeleton-block" style="height: 180px" />
      <div class="skeleton-line title" />
      <div class="skeleton-line short" />
      <div class="skeleton-line" />
      <div class="skeleton-line" />
      <div class="skeleton-line short" />
    </div>
    <p v-else-if="err" class="error">{{ err }}</p>
    <article v-else-if="post" class="article-body">
      <img
        v-if="post.cover_image_url"
        class="cover"
        :src="post.cover_image_url"
        :alt="post.title"
      />
      <h1>{{ post.title }}</h1>
      <p class="meta">{{ formatDate(post.created_at) }} · 约 {{ readingMinutes }} 分钟读完</p>
      <div class="author-follow-row">
        <span class="meta">作者：{{ post.author_name || "匿名作者" }}</span>
        <button v-if="post.author_id" type="button" class="secondary small" @click="toggleFollowAuthor">
          {{ isFollowingAuthor ? "已关注" : "关注作者" }}
        </button>
      </div>
      <div class="actions-box">
        <div class="actions-row">
          <span class="icon-action stat" title="浏览量">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 5c5.6 0 9.8 4.1 11 6.9-1.2 2.8-5.4 7.1-11 7.1S2.2 14.7 1 11.9C2.2 9.1 6.4 5 12 5Zm0 2c-4.3 0-7.7 3-9 4.9 1.3 1.9 4.7 5.1 9 5.1s7.7-3.2 9-5.1C19.7 10 16.3 7 12 7Zm0 2.2a2.8 2.8 0 1 1 0 5.6 2.8 2.8 0 0 1 0-5.6Z" />
            </svg>
            <span>{{ interactionStats.view_count || 0 }}</span>
          </span>
          <button type="button" class="icon-action" :class="{ active: hasLiked }" @click="onLike" aria-label="点赞">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M9 22H5a2 2 0 0 1-2-2v-7.5A2.5 2.5 0 0 1 5.5 10H9v12Zm2-12 3-7a2 2 0 0 1 3.8.63V8h2.7A2.5 2.5 0 0 1 23 10.7l-1.3 8A3 3 0 0 1 18.75 21H11V10Z"
              />
            </svg>
            <span>{{ interactionStats.like_count || 0 }}</span>
          </button>
          <button
            type="button"
            class="icon-action"
            :class="{ active: hasFavorited }"
            @click="onFavorite"
            aria-label="收藏"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m12 18.3-6.18 3.7 1.64-7.03L2 10.24l7.19-.62L12 3l2.81 6.62 7.19.62-5.46 4.73L18.18 22z" />
            </svg>
            <span>{{ interactionStats.favorite_count || 0 }}</span>
          </button>
          <button type="button" class="icon-action" @click="toggleSharePanel" aria-label="转发">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M14 3v4.2c-6 1-8.8 4.5-10 9.8 2.4-3.1 5.2-4.5 10-4.8V17l8-7-8-7Z" />
            </svg>
            <span>{{ interactionStats.share_count || 0 }}</span>
          </button>
          <select v-model="reportReason" class="toolbar-select report-select">
            <option value="低质内容">低质内容</option>
            <option value="疑似违规">疑似违规</option>
            <option value="广告营销">广告营销</option>
          </select>
          <button type="button" class="icon-action danger" @click="onReport" aria-label="举报">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 2h2v20H4V2Zm4 2h10l-2 4 2 4H8V4Z" />
            </svg>
            <span>举报</span>
          </button>
        </div>
        <div v-if="sharePanelOpen" class="share-panel">
          <button
            v-for="opt in shareOptions"
            :key="opt.value"
            type="button"
            class="share-item"
            :class="{ active: shareChannel === opt.value }"
            @click="shareChannel = opt.value"
          >
            <i>{{ opt.icon }}</i>
            <span>{{ opt.label }}</span>
          </button>
          <button type="button" class="secondary small" @click="onShare">确认转发</button>
        </div>
      </div>
      <p v-if="interactionMsg" class="meta">{{ interactionMsg }}</p>
      <div class="prose" v-html="renderedHtml"></div>

      <section class="comments card">
        <p v-if="commentSuccess" class="comment-success">{{ commentSuccess }}</p>
        <h2 id="comment-form" class="comments-form-title">发表评论</h2>
        <ul class="comments-form-steps">
          <li>
            <strong>新评论</strong>：「作者」已生成个性化昵称（可改）；写好内容后点「发表评论」。
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
              <input
                id="cn"
                v-model="cAuthor"
                maxlength="8"
                placeholder="2～8 字昵称，已自动生成；可改或点「换一换」"
              />
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

        <div class="comments-head">
          <h3 class="comments-list-title">全部评论</h3>
          <select v-model="commentsSort" class="toolbar-select">
            <option value="hot">最热</option>
            <option value="newest">最新</option>
          </select>
        </div>
        <p v-if="cLoading" class="meta">评论加载中…</p>
        <p v-else-if="cErr" class="error">{{ cErr }}</p>
        <ul v-else class="thread">
          <CommentItem v-for="node in displayedTree" :key="node.id" :node="node" @reply="startReply" />
        </ul>
        <p v-if="!cLoading && !comments.length" class="meta empty-hint">
          暂无评论，在上方表单留言即可。
        </p>
      </section>
    </article>
    <aside v-if="post && !loading" class="article-side card">
      <section>
        <h3>作者信息</h3>
        <p class="meta">{{ post.author_name || "匿名作者" }}</p>
        <p class="meta">发布时间：{{ formatDate(post.created_at) }}</p>
      </section>
      <section v-if="tocItems.length" class="article-toc">
        <h3>目录</h3>
        <ul>
          <li v-for="item in tocItems" :key="item.id">
            <button type="button" class="toc-link" :class="`lv-${item.level}`" @click="jumpToToc(item.id)">
              {{ item.text }}
            </button>
          </li>
        </ul>
      </section>
    </aside>
  </div>
</template>

<style scoped>
.post-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 1rem;
  max-width: 1180px;
}
.cover {
  width: 100%;
  max-height: 360px;
  object-fit: cover;
  border-radius: 12px;
  margin-bottom: 1rem;
  border: 1px solid var(--border);
}
.author-follow-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin: 0.5rem 0 0.8rem;
}
.comment-success {
  margin: 0 0 1rem;
  padding: 0.65rem 0.85rem;
  font-size: 0.9rem;
  color: var(--text);
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.35);
  border-radius: 8px;
}
.comments-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
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
  background: var(--emoji-bar-bg);
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
.actions-row {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
.actions-box {
  margin: 0.8rem 0 1rem;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0.65rem;
  background: color-mix(in srgb, var(--surface) 90%, transparent);
}
.icon-action {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  border-radius: 999px;
  padding: 0.35rem 0.6rem;
  cursor: pointer;
}
.icon-action svg {
  width: 14px;
  height: 14px;
  fill: currentColor;
}
.icon-action.active {
  color: var(--accent-hover);
  border-color: var(--accent);
}
.icon-action.danger {
  color: var(--danger);
}
.icon-action.stat {
  cursor: default;
}
.report-select {
  min-width: 120px;
}
.share-panel {
  margin-top: 0.55rem;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.45rem;
}
.share-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.25rem 0.55rem;
  background: var(--surface);
  color: var(--text);
}
.share-item i {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-style: normal;
  font-size: 11px;
  border: 1px solid var(--border);
}
.share-item.active {
  border-color: var(--accent);
  color: var(--accent-hover);
}
.article-side {
  align-self: start;
  position: sticky;
  top: 1rem;
  display: grid;
  gap: 0.8rem;
  padding: 1rem;
}
.article-side h3 {
  margin: 0 0 0.35rem;
  font-size: 1rem;
}
.article-toc ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.2rem;
}
.toc-link {
  display: block;
  width: 100%;
  border: none;
  background: transparent;
  color: var(--text);
  text-align: left;
  padding: 0.2rem 0.3rem;
  border-radius: 6px;
}
.toc-link:hover {
  background: rgba(255, 255, 255, 0.06);
}
.toc-link.lv-2 {
  padding-left: 0.9rem;
}
.toc-link.lv-3 {
  padding-left: 1.4rem;
}
@media (max-width: 1080px) {
  .post-layout {
    grid-template-columns: 1fr;
  }
  .article-side {
    position: static;
  }
}
</style>
