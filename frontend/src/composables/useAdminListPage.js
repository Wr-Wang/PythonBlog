import { ref, watch } from "vue";
import { useRouter } from "vue-router";

/**
 * 后台列表页通用分页加载逻辑：
 * - 统一 page/pageSize/total/loading/error 管理
 * - 统一越界分页回退（删除后当前页无数据）
 * - 统一 401 清 token 并跳登录页
 */
export function useAdminListPage(options) {
  const {
    listFn,
    redirectPath,
    initialPageSize = 20,
    extractItems = (data) => data.items ?? data,
    extractTotal = (data) => data.total ?? 0,
    buildListParams = ({ page, pageSize }) => ({ skip: (page - 1) * pageSize, limit: pageSize }),
    onLoaded = null,
  } = options;
  const router = useRouter();

  const rows = ref([]);
  const total = ref(0);
  const page = ref(1);
  const pageSize = ref(initialPageSize);
  const loading = ref(true);
  const err = ref("");

  /**
   * 拉取列表数据并维护分页状态。
   * - 支持 skip/limit 与 page/size 两种参数构造
   * - 自动处理越界页回退
   * - 提供 onLoaded 钩子给调用页做附加加载（如 SLA）
   */
  async function load() {
    loading.value = true;
    err.value = "";
    try {
      let p = page.value;
      let params = buildListParams({ page: p, pageSize: pageSize.value });
      let { data } = await listFn(params);
      const maxP = Math.max(1, Math.ceil((extractTotal(data) || 0) / pageSize.value) || 1);
      if (p > maxP) {
        // 删除数据后可能出现“当前页超范围”，自动回到最后一页再查一次。
        page.value = maxP;
        p = maxP;
        params = buildListParams({ page: p, pageSize: pageSize.value });
        ({ data } = await listFn(params));
      }
      rows.value = extractItems(data);
      total.value = extractTotal(data);
      if (typeof onLoaded === "function") {
        // 让业务页面复用当前请求参数进行二次加载，避免重复拼装条件。
        await onLoaded({ data, params, page: p, pageSize: pageSize.value, rows: rows.value, total: total.value });
      }
    } catch (e) {
      err.value = e.response?.data?.detail || e.message || "加载失败";
      if (e.response?.status === 401) {
        // 登录态失效统一清理并带 redirect 回登录页。
        localStorage.removeItem("blog_token");
        localStorage.removeItem("blog_profile");
        router.push({ name: "admin-login", query: { redirect: redirectPath } });
      }
    } finally {
      loading.value = false;
    }
  }

  function setPage(v) {
    /** 仅更新页码，真正加载由 watch(page) 触发。 */
    page.value = v;
  }

  function onPageSizeChange(newSize) {
    /** 改每页条数时，优先回第一页，避免页码越界。 */
    pageSize.value = newSize;
    if (page.value !== 1) page.value = 1;
    else load();
  }

  // 统一入口：所有列表页都通过页码变化驱动 load。
  watch(page, load, { immediate: true });

  return {
    rows,
    total,
    page,
    pageSize,
    loading,
    err,
    load,
    setPage,
    onPageSizeChange,
  };
}

