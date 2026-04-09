# PythonBlog 详细功能设计

**文档版本：** 1.0  
**对应需求：** [`requirements.md`](./requirements.md) **v2.3**（基线 §3 为设计落地范围；扩展 §4 为规划级设计说明）  
**对应架构：** [`architecture.md`](./architecture.md)  

本文档在需求之上补充 **功能逻辑、接口与数据要点、环境与配置、错误与边界**，供开发、测试与部署对照。若需求或代码变更，请同步修订本文档。

---

## 1. 文档说明

### 1.1 设计范围

| 类别 | 内容 |
|------|------|
| **必须实现（基线）** | 与需求 §3 中 SYS / AUTH / PUB / ADM-* / UPL / FE / DEP 一致，与当前仓库实现对齐。 |
| **规划项** | 需求 §4（RBAC、MOD、DISC、SRCH、SEC、OPS、MED、IMG、VID、CNT、ACC、UXR、EDW、GRO、PRV、AXP、HUX 等）在本文 **§11** 作概要设计方向，详细规格待排期后单独立项。 |

### 1.2 术语与角色

与需求文档 §2 一致：**访客**、**管理员**（`User.is_active = true`，基线无角色细分）。

---

## 2. 系统与环境总览

### 2.1 逻辑架构（简述）

- **浏览器** → Vue 3 SPA（开发时 Vite 代理 `/api`、`/uploads`）→ **FastAPI** → **SQL Server**；静态上传文件由后端目录 + `GET /uploads/*` 提供。  
- **鉴权：** 管理类接口 `Authorization: Bearer <JWT>`；公开接口无令牌。  
- **数据库门闸：** `app.state.db_ready == False` 时，除 `GET /api/health` 外所有 `/api/*` 返回 **503**（见 [`http_middleware.py`](../backend/app/http_middleware.py)）。

### 2.2 运行环境矩阵

| 环境 | 用途 | 后端 | 前端 | 数据库 | 典型访问 |
|------|------|------|------|--------|----------|
| **本地开发** | 功能开发与调试 | `uvicorn`（如 `127.0.0.1:8000`） | Vite dev（`5173`），代理到后端 | 本机 SQL Server / 命名实例 | `http://localhost:5173` |
| **前端预览** | 构建产物联调 | 同上或仅静态 | `vite preview`（`4173`），代理同上 | 同上 | `http://localhost:4173` |
| **生产（同机）** | 单服务器部署 | Uvicorn 或 IIS HttpPlatformHandler 等（见部署文档） | `npm run build` 输出 `frontend/dist`，由 FastAPI `mount_frontend_dist` 同域托管 | 生产 SQL Server | 站点根路径 + `/api` |
| **生产（分域）** | 前后端分离 | 公网 API 域名 | 独立 CDN/静态托管 | 生产库 | 需配置 `CORS_ORIGINS` |

**说明：** 具体 IIS 站点、端口、HTTPS 证书与回收应用池等以 [`Windows11-IIS部署www-blogapi-8081.md`](./Windows11-IIS部署www-blogapi-8081.md) 等同目录文档为准。

### 2.3 依赖软件与版本（参考）

| 依赖 | 说明 |
|------|------|
| **Python** | 与 `backend` 运行环境一致（建议 3.11+，以团队约定为准）。 |
| **Node.js** | 用于构建前端（建议 LTS；与 Vite 6 兼容）。 |
| **SQL Server** | 实例与库名由 `DATABASE_URL` 指定；应用启动可配合 [`db_bootstrap`](../backend/app/db_bootstrap.py) 建库逻辑（以代码为准）。 |
| **ODBC Driver** | Windows 需安装 **ODBC Driver 17/18 for SQL Server**，且 `DATABASE_URL` 中 `driver=` 与已安装驱动名称一致（见 `backend/.env.example`）。 |
| **Python 包** | 见 [`backend/requirements.txt`](../backend/requirements.txt)：`fastapi`、`uvicorn`、`sqlalchemy`、`pyodbc`、`python-jose`、`bcrypt`、`pydantic-settings` 等。 |
| **前端包** | 见 [`frontend/package.json`](../frontend/package.json)：`vue`、`vue-router`、`axios`、`marked` 等。 |

### 2.4 目录与产物

| 路径 | 说明 |
|------|------|
| `backend/.env` | 本地/服务器环境变量（不入库，见 `.gitignore`）。 |
| `backend/uploads/` | 默认上传根目录（`upload_dir`），生产需备份与磁盘监控。 |
| `frontend/dist/` | 前端构建产物；存在时后端挂载 SPA。 |

---

## 3. 配置设计

### 3.1 配置来源与优先级

- 使用 **Pydantic Settings**：环境变量与 `backend/.env` 合并，键名与 [`config.py`](../backend/app/config.py) 字段对应（如 `DATABASE_URL` → `database_url`）。  
- **生产建议：** 敏感项以系统环境变量或密钥管理注入，避免在磁盘长期存放弱口令。

### 3.2 基线配置项（功能含义）

| 变量 | 功能设计要点 |
|------|----------------|
| `DATABASE_URL` | **必填**。仅允许 `mssql+pyodbc://`；含主机、库名、驱动、信任证书等。连接失败时 `lifespan` 捕获异常，`db_ready=False`，健康检查返回降级信息。 |
| `SECRET_KEY` | JWT 签名密钥；**生产必须替换**默认字符串。泄露可导致伪造任意用户身份。 |
| `ALGORITHM` | 默认 `HS256`；与签发、校验一致。 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 默认约 24 小时；过期后接口 **401**。 |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 仅在 **库中不存在该用户名** 时种子创建管理员；已有用户则不会覆盖密码。 |
| `CORS_ORIGINS` | 逗号分隔；与浏览器实际访问前端的 Origin 一致。生产若同域托管前端，可缩窄来源。 |
| `upload_dir` | 上传文件物理路径；进程需写权限；与 `GET /uploads` 映射一致。 |

### 3.3 规划项配置（需求 §7）

速率限制、SMTP、对象存储、站点公开 URL、主题预设等：**待实现后** 增补 `config.py` 与本表。

---

## 4. 系统启动与健康检查（需求 SYS-*）

### 4.1 功能设计

1. **启动阶段（lifespan）**  
   - 尝试确保数据库存在、建表、`db_init`（种子用户/分类/标签/示例文章）。  
   - 成功：`app.state.db_ready = True`。  
   - 失败：记录 `app.state.db_error`，`db_ready=False`，进程仍可响应 HTTP。

2. **API 门闸**  
   - 路径以 `/api` 开头且 **不是** `/api/health`：若 `db_ready` 为假，直接 **503 JSON**，文案提示检查 SQL Server 与 `DATABASE_URL`（与需求 SYS-02 一致）。

3. **健康检查 `GET /api/health`**  
   - 始终可访问；返回 `status`（`ok`/`degraded`）与 `database`（`ok` 或错误字符串）。运维与前端可用其判断「仅 DB 故障」场景。

### 4.2 验收对应

需求 **SYS-01～SYS-05**；测试建议：故意错误连接串启动，确认 **503** 与健康检查内容。

---

## 5. 认证与鉴权（需求 AUTH-*）

### 5.1 功能设计

| 能力 | 设计要点 |
|------|----------|
| **登录** `POST /api/auth/login` | Body：`username`、`password`。查库比对；密码经 `verify_password`（bcrypt + SHA256 预处理或兼容旧 bcrypt）。失败统一 **401** 文案「用户名或密码错误」。 |
| **禁用用户** | `is_active=False` → **403**「账户已禁用」。 |
| **JWT** | Payload：`sub`=用户名，`exp` 过期时间；对称密钥 `SECRET_KEY`。 |
| **受保护路由** | `Depends(get_current_user)`：无 Bearer → **401**；JWT 无效/过期 → **401**；用户不存在或禁用 → **401**。 |
| **登出** | `POST /api/auth/logout` 占位；**设计约定**：以客户端删除 `localStorage` 中 token 为准（需求 AUTH-05）。 |

### 5.2 前端约定

- Token 存 **`blog_token`**（见 [`frontend/src/api/http.js`](../frontend/src/api/http.js)）；请求头 `Authorization: Bearer ...`。  
- 路由 [`router/index.js`](../frontend/src/router/index.js)：`meta.requiresAuth` 无 token 跳转登录页并带 `redirect`。

### 5.3 验收对应

AUTH-01～AUTH-05；非法/过期 token 调管理接口应 **401**。

---

## 6. 访客端：文章与列表（需求 PUB-01～PUB-04）

### 6.1 功能设计

| 接口（基线） | 行为 |
|--------------|------|
| `GET /api/posts` | Query：`published_only`（默认 true）、`skip`、`limit`。仅返回已发布文章列表项字段（`PostListItem`）。 |
| `GET /api/posts/by-slug/{slug}` | 若文章不存在或 **未发布** → **404**。 |
| 首页 `HomeView` | 调用 `getPosts({ published_only: true })`，展示标题、摘要、日期，链到 `/post/:slug`。 |
| 详情 `PostView` | 按 slug 拉取文章；正文用 **marked** 渲染 Markdown（实现以代码为准）；展示元信息与封面等字段。 |

### 6.2 数据与规则

- **slug** 全局唯一；由后台创建/更新时校验（ADM-P-03/04）。  
- 访客 **永远不能** 通过公开接口看到未发布文章（PUB-02）。

### 6.3 验收对应

PUB-01～PUB-04；未发布 slug 访问 **404**。

---

## 7. 访客端：评论（需求 PUB-05、PUB-06）

### 7.1 功能设计

| 接口 | 行为 |
|------|------|
| `GET /api/comments/by-post/{post_id}` | 文章须存在且 **已发布**；否则 **404**。返回该文下评论，排序以代码为准（通常按时间）。 |
| `POST /api/comments/by-post/{post_id}` | Body：作者昵称、内容、可选 `parent_id`（回复）。校验父评论同文；成功 **201**。 |

### 7.2 嵌套展示

- 前端将 `parent_id` 组装为树形或线程结构（见 `PostView` / `CommentItem`）；**需求 ADM-M-03** 要求后台与公开校验规则一致。

### 7.3 验收对应

PUB-05、PUB-06；对未发布文章拉评或发评 **404**。

---

## 8. 后台：文章管理（需求 ADM-P-*）

### 8.1 功能设计

| 接口 | 权限 | 要点 |
|------|------|------|
| `GET /api/posts/admin` | JWT | 全部文章含未发布；分页 `skip`/`limit`。 |
| `GET /api/posts/admin/{id}` | JWT | 单篇管理视图。 |
| `POST /api/posts` | JWT | 创建：`slug` 唯一；`category_id` 须存在；`tag_ids` 绑定；`author_id=current.id`；可含 `cover_image_url`。 |
| `PATCH /api/posts/{id}` | JWT | 更新字段；改 slug 时查重。 |
| `DELETE /api/posts/{id}` | JWT | 物理删除或逻辑以代码为准（当前实现为删除）。 |

### 8.2 业务规则

- **分类**：`ensure_category_exists` 防止无效分类。  
- **标签**：`set_post_tags` 维护多对多关系。  
- **正文**：长文本存 `content`；媒体 URL 可为站内 `/uploads/...` 或外链（基线不校验外链白名单，扩展 VID-01 将约束嵌入）。

### 8.3 验收对应

ADM-P-01～ADM-P-05。

---

## 9. 后台：分类与标签（需求 ADM-C-*、ADM-T-*）

### 9.1 功能设计

- **分类** ` /api/categories/admin* `：**slug 唯一**；更新时若改 slug 需排除自身查重。删除：若 DB 外键阻止删除，返回约束错误（运维需先迁移文章）。  
- **标签** ` /api/tags/admin* `：**slug 唯一**；删除标签清理与文章的关联（级联或等价逻辑，见模型）。

### 9.2 验收对应

ADM-C-01～ADM-C-02，ADM-T-01。

---

## 10. 后台：用户与评论管理

### 10.1 用户（需求 ADM-U-*）

- CRUD：`/api/users/admin` 系列；创建/更新密码经 `hash_password` 入库。  
- **删除禁止**：`user_id == current.id` → **400**「不能删除当前登录用户」（ADM-U-04）。

### 10.2 评论（需求 ADM-M-*）

- 全站列表、单条 CRUD：`/api/comments/admin` 系列；可代发评论；规则与公开接口对 `post_id`/`parent_id` 一致。

---

## 11. 文件上传（需求 UPL-*）

### 11.1 功能设计

- **接口** `POST /api/upload/image`：需 JWT；`multipart` 单文件。  
- **允许类型**：`image/jpeg`、`image/png`、`image/gif`、`image/webp`。  
- **大小**：≤ **5MB**，超限 **400**。  
- **存储**：`upload_dir` 下 UUID 文件名；响应相对 URL `/uploads/...`（UPL-03）。  
- **访问**：`main.py` 挂载 `StaticFiles`；开发时 Vite 代理 `/uploads`（UPL-04）。

### 11.2 安全与扩展

- 基线 **不** 做图片内容魔数深度校验；生产可加强。  
- 扩展 **MED/IMG** 将引入 WebP、缩略图、媒体库元数据等（见需求 §4）。

---

## 12. 前端路由与构建（需求 FE-*、DEP-*）

### 12.1 路由

| 路径 | 说明 |
|------|------|
| `/` | 首页列表 |
| `/post/:slug` | 文章详情 |
| `/admin/login` | 登录 |
| `/admin/*` | `AdminLayout` 子路由，需 token（见 FE-01） |

### 12.2 构建与托管

- **开发**：`npm run dev`，环境变量与代理见 [`vite.config.js`](../frontend/vite.config.js)。  
- **生产**：`npm run build` → `frontend/dist`；若目录存在，FastAPI 挂载 SPA 并 History fallback（DEP-01）；否则根路径 JSON 提示（DEP-02）。

---

## 13. 非功能设计摘要（对应需求 §6）

| 维度 | 基线实现要点 | 规划（需求 §4/§6） |
|------|----------------|---------------------|
| **安全** | 密码哈希、JWT、HTTPS 部署侧；无内置速率限制 | SEC-*、CSP/iframe 白名单 |
| **性能** | 分页、ORM；无强制缓存 | 索引、N+1、CDN、图片懒加载 |
| **可用性** | `detail` 错误体；503 DB 门闸 | OPS 健康检查扩展 |
| **体验/HUX** | 未强制设计体系 | HUX 令牌、空状态、骨架屏等 |

---

## 14. 扩展需求概要设计（需求 §4，规划项）

以下为 **概要级**，避免与需求表重复；落地时需单独详细设计与评审。

| 分组 | 概要设计方向 |
|------|----------------|
| **RBAC** | `User` 增角色或独立角色表；依赖注入按角色过滤路由。 |
| **MOD** | `Comment` 增 `status`；公开列表 `approved`；后台审核流。 |
| **DISC** | RSS/sitemap 路由；OG/meta；JSON-LD；`canonical` 需站点 `PUBLIC_BASE_URL` 配置。 |
| **SRCH** | 新 `GET /api/posts/search?q=` 或全文索引；仅已发布。 |
| **SEC** | 中间件限流（IP+路径）；429。 |
| **OPS** | 健康检查附带版本号、DB 延迟。 |
| **MED/IMG/VID/CNT** | 媒体表、转码任务队列（可选）、Markdown 扩展与白名单 iframe。 |
| **UXR/EDW/GRO/PRV/AXP** | 阅读时间字段或前端计算；定时发布调度器；相关文章算法；Cookie 横幅组件；PWA manifest；i18n 资源文件。 |
| **HUX** | CSS 变量主题；空/加载/错误组件规范；触控最小尺寸。 |

---

## 15. 测试与验收映射

| 需求章节 | 本文档章节 | 说明 |
|----------|------------|------|
| §3.1 SYS | §4 | 启动、503、health |
| §3.2 AUTH | §5 | 登录、JWT、401/403 |
| §3.3 PUB | §6、§7 | 文章、评论 |
| §3.4～3.7 ADM | §8～§10 | 后台 CRUD |
| §3.8 UPL | §11 | 上传 |
| §3.9～3.10 FE/DEP | §12 | 路由与构建 |
| §8.1 基线验收 | 各节「验收对应」 | 端到端用例建议与 [`requirements.md`](./requirements.md) §8.1 一致 |

---

## 16. 文档维护

- 需求变更（[`requirements.md`](./requirements.md)）或架构变更（[`architecture.md`](./architecture.md)）时，更新本设计中的 **环境、接口、规则** 描述。  
- **扩展需求** 一旦纳入基线，应将对应章节从 §14 下沉为与 §4～§12 同级的详细设计，并更新版本号。

*本文档随代码演进更新。*
