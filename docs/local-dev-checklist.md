# 本机开发 — 最小检查清单（打勾表）

适用：**仅在个人电脑上开发 PythonBlog**，不对接生产 IIS/域名。完成一项勾一项。

---

## 1. 软件已安装

| 序号 | 检查项 | 完成 |
|------|--------|:----:|
| 1.1 | 已安装 **Python 3.11+**（或团队约定版本），命令行可执行 `python --version` | [ ] |
| 1.2 | 已安装 **Node.js LTS**，命令行可执行 `node -v`、`npm -v` | [ ] |
| 1.3 | 已安装 **SQL Server**（本机实例或 Docker 等），服务可启动且能用 SSMS/命令行连接 | [ ] |
| 1.4 | 已安装 **ODBC Driver 17 或 18 for SQL Server**（与 `DATABASE_URL` 里 `driver=` 名称一致） | [ ] |
| 1.5 | （可选）已安装 **Git**，用于克隆/拉代码 | [ ] |

---

## 2. 仓库与依赖

| 序号 | 检查项 | 完成 |
|------|--------|:----:|
| 2.1 | 已克隆或解压项目到本机目录 | [ ] |
| 2.2 | 在 `backend` 下创建虚拟环境并 **激活** | [ ] |
| 2.3 | 已执行 `pip install -r requirements.txt` 且无报错 | [ ] |
| 2.4 | 在 `frontend` 下已执行 `npm install` 且无报错 | [ ] |

---

## 3. 配置与数据库

| 序号 | 检查项 | 完成 |
|------|--------|:----:|
| 3.1 | 已复制 `backend/.env.example` 为 `backend/.env` | [ ] |
| 3.2 | `DATABASE_URL` 已改为你的本机实例（`mssql+pyodbc://...`，库名/用户/密码/命名实例写法正确） | [ ] |
| 3.3 | `SECRET_KEY` 已改为随机长字符串（本机也建议勿用默认值） | [ ] |
| 3.4 | `CORS_ORIGINS` 包含 `http://localhost:5173` 与 `http://127.0.0.1:5173`（默认已含则可跳过） | [ ] |
| 3.5 | SQL Server 上已存在目标库，或确认应用有权 **自动建库**（以你环境为准） | [ ] |

---

## 4. 启动与验证

| 序号 | 检查项 | 完成 |
|------|--------|:----:|
| 4.1 | 在 **`backend` 目录**下启动 API：执行 `python run.py`（默认 `0.0.0.0:8000`，热重载） | [ ] |
| 4.2 | 浏览器访问 `http://127.0.0.1:8000/api/health` 返回 JSON，且 `status` 为 `ok`、`database` 为 `ok` | [ ] |
| 4.3 | 在 `frontend` 下执行 `npm run dev`，无报错 | [ ] |
| 4.4 | 浏览器打开 `http://localhost:5173`，首页能加载文章列表（或空列表无白屏报错） | [ ] |
| 4.5 | 能打开 `http://localhost:5173/admin/login` 并用种子账号登录（默认见 `.env` 中 `ADMIN_USERNAME`/`ADMIN_PASSWORD`） | [ ] |

---

## 5. 常见问题（本机）

| 现象 | 可检查 |
|------|--------|
| `/api/health` 中 database 报错 | `DATABASE_URL`、SQL 服务是否启动、ODBC 驱动名、防火墙、命名实例 `%5C` 转义 |
| 前端有页面但无数据 | 后端是否 8000 运行、Vite 是否代理 `/api`（见 `vite.config.js`） |
| 登录后 401 | `localStorage` 中 token、`CORS_ORIGINS`、后端与前端是否同源代理 |
| 上传图片失败 | `backend/uploads` 是否可写、是否超过 5MB、MIME 是否允许 |

---

*更完整的环境说明见 [`functional-design.md`](./functional-design.md) §2；需求见 [`requirements.md`](./requirements.md)。*
