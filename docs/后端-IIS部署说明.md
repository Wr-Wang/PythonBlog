# 后端 IIS 部署说明（示例：www.blogapi.com:80）

本文档说明在 **Windows Server / Windows 10+ IIS** 上托管本项目的 **FastAPI** 后端，访问方式为 **`http://www.blogapi.com:80`**（可按需改为 HTTPS）。

---

## 1. 架构说明

| 项目 | 说明 |
|------|------|
| **对外** | 浏览器访问 **`http://www.blogapi.com:80`**（主机名 + 端口由 **IIS 站点绑定**） |
| **对内** | **HttpPlatformHandler** 启动 **`python -m iis_entry`**（见 **`backend/iis_entry.py`**），从环境变量 **`HTTP_PLATFORM_PORT`** 读端口后启动 uvicorn；**勿**在命令行写死 80（对外端口仅由 IIS 绑定） |
| **代码目录** | IIS 网站**物理路径**建议指向仓库中的 **`backend`** 文件夹（内含 `app/`、`venv/`、`web.config`） |

---

## 2. 前置条件

1. 已安装 **IIS**（「启用或关闭 Windows 功能」中勾选 **Web 管理工具**、**万维网服务**）。
2. 安装 **[HttpPlatformHandler](https://www.iis.net/downloads/microsoft/httpplatformhandler)**（与 IIS 位数一致，x64/x86）。
3. 安装 **Python 3.10+** 与本机 **SQL Server** 或远程库；安装 **Microsoft ODBC Driver for SQL Server**（与 `DATABASE_URL` 中 `driver=` 一致）。
4. 在 `backend` 下创建虚拟环境并安装依赖：

```bat
cd C:\部署路径\PythonBlog\backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

5. 复制 **`backend/.env.example`** 为 **`backend/.env`**，填写 **`DATABASE_URL`**、**`SECRET_KEY`** 等（生产 **`SECRET_KEY` 必须更换**）。

6. （可选）若需同域提供前端页面，在**项目根**执行 `cd frontend && npm run build`，保证存在 **`frontend/dist`**。

### 2.1 一键生成「发布文件」（推荐）

在开发机进入 **`backend`** 目录，用 PowerShell 执行：

```powershell
cd C:\path\to\PythonBlog\backend
.\scripts\publish-for-iis.ps1
```

| 参数 | 说明 |
|------|------|
| **`-BackendRoot "D:\Sites\PythonBlog\backend"`** | 可选。若提供服务器上将要部署的 **backend 绝对路径**，生成的 **`web.config`** 会直接写入 `processPath` 与 `PYTHONPATH`；否则使用占位符 **`BACKEND_ROOT_PLACEHOLDER`**，部署时在服务器上全文替换为实际路径。 |
| **`-Zip`** | 额外生成 **`backend/iis-backend-publish.zip`**，便于拷贝到服务器解压。 |
| **`-OutputDir`** | 自定义输出目录（默认：`backend/iis-publish-artifacts/`）。 |

生成结果包含：

- **`app/`**（源码，已排除 `__pycache__`）
- **`iis_entry.py`**（IIS 启动入口，见下文 **502.3** 说明）
- **`requirements.txt`**
- **`web.config`**（`arguments="-m iis_entry"`）
- **`README-IIS-Deploy.txt`**（部署步骤，英文文件名避免乱码）
- **`.env.example`**（若仓库中存在）

> 默认输出目录与 zip 已列入 **`backend/.gitignore`**，避免误提交；发布包请在服务器上解压后配置 **venv**、**`.env`**、**`logs`** 目录。

若未使用脚本，也可手动复制 **`backend/web.config.example`** 为 **`web.config`** 并按下面章节修改路径。

---

## 3. 配置 web.config

1. 将 **`backend/web.config.example`** 复制为 **`backend/web.config`**（或直接使用 **`publish-for-iis.ps1`** 生成的 **`web.config`**）。
2. 把文件中 **`须修改`** 的两处路径改为本机 **`backend`** 的绝对路径，例如：
   - `processPath`：`D:\Sites\PythonBlog\backend\venv\Scripts\python.exe`
   - `PYTHONPATH`：`D:\Sites\PythonBlog\backend`
3. 若希望在配置中注入环境变量（不推荐把密钥写入可被多人读取的明文），可在 `<environmentVariables>` 中增加 **`DATABASE_URL`**、**`SECRET_KEY`**、**`CORS_ORIGINS`**；更推荐在 **IIS 管理器 → 站点 → 配置编辑器 → system.webServer/httpPlatform/environmentVariables** 中配置，或对应用池使用**用户级环境变量**。

### 3.1 CORS 与域名

若前端与 API **同源**（例如静态页也由本站点提供），可保持默认。若前端在其它域名，请在 **`backend/.env` 或环境变量**中设置，例如：

```env
CORS_ORIGINS=https://你的前端域名,http://localhost:5173
```

API 自身地址为 **`https://www.blogapi.com:80`** 时，通常**不必**把 API 域名写进 `CORS_ORIGINS`（浏览器同源策略针对的是**页面所在源**，不是 API 地址本身）；仅当**浏览器页面**在别的源访问该 API 时，需要把**页面源**列入 `CORS_ORIGINS`。

---

## 4. 新建 IIS 网站

1. 打开 **IIS 管理器** → 右键「网站」→ **添加网站**。
2. **网站名称**：如 `BlogAPI`。
3. **物理路径**：选到仓库的 **`backend`** 目录（内含 `web.config`）。
4. **绑定**：
   - **类型**：`http`（若已配置证书可再添加 `https`）。
   - **IP 地址**：全部未分配或本机 IP。
   - **端口**：**`80`**。
   - **主机名**：**`www.blogapi.com`**。
5. **应用程序池**：无托管代码（HttpPlatformHandler 启动外部进程，与 .NET CLR 无关）；可将「.NET CLR 版本」设为**无托管代码**。
6. 确认 **`backend\logs`** 目录存在（`web.config` 中 `stdoutLogFile` 使用 `.\logs\stdout`，首次可手动建 `logs` 文件夹），否则日志可能失败；失败时可暂时关闭 `stdoutLogEnabled` 排查。

---

## 5. DNS 与防火墙

| 项 | 说明 |
|----|------|
| **DNS** | 将 **`www.blogapi.com`** 的 **A 记录** 指向本服务器公网 IP（内网测试可改 **hosts**：`127.0.0.1 www.blogapi.com`）。 |
| **防火墙** | 入站规则放行 **TCP 80**（若仅本机访问可不改）。 |

---

## 6. HTTPS（可选）

在 IIS 站点 → **绑定** → 添加 **`https`**，端口可用 **8443** 或 **443**（若 443 已被占用则错开端口）。在服务器上申请/安装证书后，客户端使用 `https://www.blogapi.com:端口` 访问；同时把前端的 `CORS_ORIGINS`、反向代理配置中的 URL 改为 **https**。

---

## 7. 验证

- 浏览器访问：`http://www.blogapi.com:80/api/health`
- 应返回 JSON，`status` 为 `ok` 且数据库正常时 `database` 为 `ok`。
- Swagger：`http://www.blogapi.com:80/docs`

若 **503** 或 500，查看 **`backend/logs`** 下 stdout 日志，并核对 **`.env`**、**ODBC**、**SQL Server** 是否可达。

### 7.1 HTTP 502.3 - Bad Gateway（There was a connection error while trying to route the request）

表示 **IIS / HttpPlatformHandler 无法与后端子进程建立连接**，常见原因与处理如下。

| 原因 | 处理 |
|------|------|
| **`--port %HTTP_PLATFORM_PORT%` 未展开** | 部分环境下 web.config 里 **`%HTTP_PLATFORM_PORT%`** 不会传给 uvicorn，进程监听端口错误即会 **502.3**。请改用仓库中的 **`iis_entry.py`**，并在 **`web.config`** 中写 **`arguments="-m iis_entry"`**（已由 **`web.config.example`** 与 **`publish-for-iis.ps1`** 生成）。部署后确认 **`backend` 根目录存在 `iis_entry.py`**。 |
| **Python 路径错误** | `processPath` 必须指向 **`venv\Scripts\python.exe`** 的真实绝对路径；应用池用户对 **`venv`**、**`app`** 有读取与执行权限。 |
| **PYTHONPATH 错误** | 须为 **`backend` 根目录**（包含 **`app`** 包与 **`iis_entry.py`** 的目录），与 IIS 站点物理路径一致。 |
| **应用启动即崩溃** | 在服务器 **`backend`** 目录打开 **cmd**，执行：`set HTTP_PLATFORM_PORT=8765` 然后 **`venv\Scripts\python.exe -m iis_entry`**，看控制台报错（缺依赖、`.env`、数据库连不上等）。 |
| **缺 `logs` 目录** | 创建 **`backend\logs`**；或暂时将 **`stdoutLogEnabled="false"`** 排除日志路径问题。 |
| **使用 ARR 反代** | 若站点实际是 **反向代理** 到本机其它端口，502.3 表示 **后端进程未监听** 或防火墙拦截；请确认被代理地址可访问。 |

更新 **`web.config`** 并放入 **`iis_entry.py`** 后，**重启站点**或 **回收应用程序池** 再测。

---

## 8. 备选：IIS 反向代理 + 独立 uvicorn

若不使用 HttpPlatformHandler，可：

1. 用 **nssm** / **计划任务** 在后台常驻：

   `uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4`

2. 安装 **Application Request Routing (ARR)** 与 **URL Rewrite**，站点绑定仍为 **`www.blogapi.com:80`**，规则将请求**反向代理**到 `http://127.0.0.1:8000`。

此方式便于与 **Windows 服务**、**进程守护** 结合，但需单独维护 uvicorn 进程。

---

## 9. Windows 11 快速步骤（合并版）

适用于本仓库在 Windows 11 本机或同类环境快速落地：

1. 启用 IIS，安装 HttpPlatformHandler。  
2. 安装 Python 3.10+、SQL Server ODBC Driver。  
3. 在 `backend` 下创建 venv 并安装依赖：`pip install -r requirements.txt`。  
4. 配置 `backend/.env`（至少 `DATABASE_URL`、`SECRET_KEY`、`CORS_ORIGINS`）。  
5. 前端构建：`cd frontend && npm run build`（生成 `frontend/dist`）。  
6. 复制 `backend/web.config.example` 为 `backend/web.config`，设置 `processPath` 与 `PYTHONPATH`。  
7. 为应用程序池身份授予 `backend` 与 Python 目录读取/执行权限（可用 `backend/scripts/ensure-iis-acls.ps1`）。  
8. IIS 新建站点 `BlogAPI`：物理路径指向 `backend`，绑定 `http/*:80:www.blogapi.com`。  
9. 回收应用程序池并验证：
   - `http://www.blogapi.com:80/api/health`
   - `http://www.blogapi.com:80/docs`
   - `http://www.blogapi.com:80/`

---

## 10. 同端口前后端原理（合并版）

本项目并不是两个服务同时监听 80，而是：

- **IIS** 监听 `80`，通过 HttpPlatformHandler 转发到 Python 子进程。  
- **Uvicorn + FastAPI** 在同一进程内按路径处理：`/api/*`、`/docs`、`/uploads/*`、`/` 与 `/assets/*`。  
- 浏览器始终只看到 `www.blogapi.com:80`，因此同源访问 `/api` 不触发跨域。  

一句话：**同端口来自“一个 FastAPI 进程同时提供 API 与静态前端”，不是两个程序共占一个端口。**

---

## 11. 相关文档

- [IIS前后端部署.md](./IIS前后端部署.md)（同一站点目录结构与 `web.config` 模板）
- [后端部署说明.md](./后端部署说明.md)（裸机 uvicorn）
- [后端目录与文件说明.md](./后端目录与文件说明.md)
