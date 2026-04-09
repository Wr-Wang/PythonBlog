# Windows 11 + IIS 部署（www.blogapi.com:8081）

本文档按顺序说明在本机或服务器上部署 **PythonBlog** 后端（FastAPI），使浏览器可通过 **`http://www.blogapi.com:8081`** 访问 API 与（可选）前端静态页。

---

## 0. 部署完成后应可访问的地址

| 用途 | URL |
|------|-----|
| 健康检查 | `http://www.blogapi.com:8081/api/health` |
| Swagger | `http://www.blogapi.com:8081/docs` |
| 站点首页 | `http://www.blogapi.com:8081/`（需已执行 `frontend` 的 `npm run build` 生成 `frontend/dist`） |

**本机解析**：在 **`C:\Windows\System32\drivers\etc\hosts`** 增加一行（需管理员保存）：

```text
127.0.0.1    www.blogapi.com
```

公网访问时，在 DNS 中为 **`www.blogapi.com`** 配置 **A 记录** 指向服务器公网 IP，并放行防火墙 **TCP 8081**。

---

## 1. 安装组件

### 1.1 启用 IIS

1. **Win + R** → `optionalfeatures` → 回车。  
2. 勾选 **Internet Information Services** → 展开并勾选 **万维网服务**、**管理工具**（含 IIS 管理控制台）。  
3. 确定并等待安装完成。

### 1.2 安装 HttpPlatformHandler

1. 打开：<https://www.iis.net/downloads/microsoft/httpplatformhandler>  
2. 下载与系统位数一致的 **x64** 安装包并安装。  
3. 安装后可在 **IIS 管理器 → 服务器 → 模块** 中看到 **httpPlatformHandler**。

### 1.3 Python、ODBC、SQL Server

1. 从 <https://www.python.org/downloads/> 安装 **Python 3.10+**（建议 3.12），安装时勾选 **Add python.exe to PATH**。  
2. 安装 **Microsoft ODBC Driver 17 or 18 for SQL Server**。  
3. 安装并启动 **SQL Server**（本机或远程），创建或使用数据库 **BlogDB**（亦可在应用首次启动时由程序创建库，见 `db_bootstrap`）。

---

## 2. 放置代码

将整个 **`PythonBlog`** 仓库放到固定目录，例如：

```text
e:\Demo\Cursor\PythonBlog\
├── backend\          ← IIS 站点「物理路径」指向此文件夹
├── frontend\         ← 构建后需存在 frontend\dist（与 backend 同级）
└── ...
```

---

## 3. Python 依赖

打开 **cmd**（或 PowerShell）：

```bat
cd /d e:\Demo\Cursor\PythonBlog\backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

若 **仅** 给 IIS 使用「系统已安装的 Python」（见下文 **web.config** 方案 B），也可在**同一解释器**上执行：

```bat
python -m pip install -r requirements.txt
```

---

## 4. 环境变量 `backend\.env`

复制 **`backend\.env.example`** 为 **`backend\.env`**，至少配置：

```env
DATABASE_URL=mssql+pyodbc://用户:密码@服务器/BlogDB?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
SECRET_KEY=请使用足够长的随机串
CORS_ORIGINS=http://www.blogapi.com:8081,http://localhost:5173
```

**同源**仅通过浏览器访问 `http://www.blogapi.com:8081` 时，将 **`http://www.blogapi.com:8081`** 写入 **`CORS_ORIGINS`** 即可。

---

## 5. 前端静态资源（可选）

在 **`frontend`** 目录：

```bat
cd /d e:\Demo\Cursor\PythonBlog\frontend
npm ci
npm run build
```

完成后应存在 **`e:\Demo\Cursor\PythonBlog\frontend\dist`**（含 `index.html`）。未构建时，访问根路径 **`/`** 会返回 JSON 提示，**`/api` 与 `/docs` 仍可用**。

**重要（IIS 已在跑时）**：`main.py` 在进程启动时决定是否挂载 `frontend/dist`。若先起了 IIS、后第一次执行 `npm run build`，需在 **IIS 管理器 → 应用程序池** 中对站点使用的池执行 **「回收」**（或 `appcmd recycle apppool /apppool.name:你的池名`），否则 **`/`** 仍可能返回「尚未构建前端」的 JSON。更新 `dist` 后同样建议回收一次。

---

## 6. 配置 `backend\web.config`

在 **`backend`** 目录放置 **`web.config`**（可由 **`web.config.example`** 复制后修改）。

- **`processPath`**：指向将运行 **`-m iis_entry`** 的 **`python.exe`**（见仓库 **`backend\iis_entry.py`**）。  
- **`PYTHONPATH`**：必须为 **`backend` 文件夹的绝对路径**（包含 `app` 包）。

### 方案 A：使用虚拟环境内的 Python（开发机常见）

```xml
<httpPlatform
  processPath="e:\Demo\Cursor\PythonBlog\backend\venv\Scripts\python.exe"
  arguments="-m iis_entry"
  ...
>
  <environmentVariables>
    <environmentVariable name="PYTHONPATH" value="e:\Demo\Cursor\PythonBlog\backend" />
  </environmentVariables>
</httpPlatform>
```

若 stdout 日志出现 **`No Python at '…Python312\python.exe'`**，多为 **venv 在 IIS 应用池身份下解析基础解释器失败**，可改用方案 B。

### 方案 B：使用本机已安装依赖的系统 Python（推荐用于本机 IIS）

将 **`processPath`** 设为本机 **`python.exe`** 绝对路径（与 **`pip install -r requirements.txt`** 所用解释器一致），**`PYTHONPATH`** 仍为 **`backend` 根目录**，例如：

```xml
<httpPlatform
  processPath="C:\Users\你的用户名\AppData\Local\Programs\Python\Python312\python.exe"
  arguments="-m iis_entry"
  ...
>
```

### 日志目录

创建目录 **`backend\logs`**（与 `stdoutLogFile=".\logs\stdout"` 对应）。

---

## 7. 权限（重要，否则易 502.3 / 0x80070005）

IIS 默认使用应用程序池身份（如 **`IIS AppPool\DefaultAppPool`**），必须对该身份授予：

1. **`backend` 整个目录**：读取与执行（至少 **RX**）。  
2. **实际使用的 `python.exe` 所在目录**（及子目录）：至少 **RX**（否则无法加载解释器与扩展模块）。

**以管理员身份**打开 **PowerShell**，将路径换成你的实际路径后执行：

```powershell
icacls "e:\Demo\Cursor\PythonBlog\backend" /grant "IIS AppPool\DefaultAppPool:(OI)(CI)RX" /T
icacls "C:\Users\你的用户名\AppData\Local\Programs\Python\Python312" /grant "IIS AppPool\DefaultAppPool:(OI)(CI)RX" /T
```

若你为站点**单独新建了应用程序池**（例如 **`BlogAPIPool`**），将上面 **`IIS AppPool\DefaultAppPool`** 改为 **`IIS AppPool\BlogAPIPool`**。

项目内提供脚本 **`backend/scripts/ensure-iis-acls.ps1`**（可传 `-BackendRoot`、`-PythonHome`）用于批量设置。

---

## 8. 在 IIS 中新建网站

### 8.1 图形界面

1. 打开 **IIS 管理器** → 右键「网站」→ **添加网站**。  
2. **网站名称**：例如 `BlogAPI`。  
3. **物理路径**：**`e:\Demo\Cursor\PythonBlog\backend`**（必须指向 **`backend`**，不是仓库根目录）。  
4. **绑定**：  
   - 类型：**http**  
   - IP：全部未分配  
   - **端口：`8081`**  
   - **主机名：`www.blogapi.com`**  
5. **应用程序池**：可使用默认池或新建；若使用 **无托管代码** / **.NET CLR 版本：无托管代码** 更清晰（与 HttpPlatformHandler 托管 Python 一致）。

### 8.2 命令行（示例）

在**管理员** **cmd** 中（路径按实际修改）：

```bat
%windir%\system32\inetsrv\appcmd.exe add site /name:BlogAPI /bindings:http/*:8081:www.blogapi.com /physicalPath:e:\Demo\Cursor\PythonBlog\backend
```

若站点已存在，仅需调整绑定或物理路径，请在 **IIS 管理器** 中编辑对应网站。

---

## 9. 回收应用程序池与验证

修改 **`web.config`** 或 **`.env`** 后：

1. **IIS 管理器** → **应用程序池** → 选中站点使用的池 → **回收**。  
2. 浏览器访问：  
   - `http://www.blogapi.com:8081/api/health` → 应返回 JSON，`database` 为 `ok` 表示数据库正常。  
   - `http://www.blogapi.com:8081/docs` → Swagger。

排错：查看 **`backend\logs`** 下 **`stdout_*.log`**；说明见 **[后端-IIS部署说明.md](./后端-IIS部署说明.md)**（502.3、路径、**`HTTP_PLATFORM_PORT`** 等）。

---

## 10. 防火墙

若需局域网或公网访问本机 **8081**：

- **Windows 防火墙** → **入站规则** → 新建 → **端口** → **TCP 8081** → 允许连接。

---

## 11. 相关文件索引

| 文件 | 说明 |
|------|------|
| [IIS同端口前后端原理.md](./IIS同端口前后端原理.md) | **为何一个端口能同时访问页面与 API**（IIS → HttpPlatformHandler → FastAPI 路由） |
| `backend/web.config` | 本机 IIS 配置（**勿**提交含敏感路径到公共仓库时可加入 `.gitignore`） |
| `backend/web.config.example` | 模板 |
| `backend/iis_entry.py` | 从 **`HTTP_PLATFORM_PORT`** 启动 uvicorn |
| `docs/后端-IIS部署说明.md` | 502.3、HTTPS、ARR 备选 |
| `docs/IIS前后端部署.md` | 前后端目录关系 |

---

## 12. 与本仓库已执行的一次性操作（参考）

在 **`e:\Demo\Cursor\PythonBlog`** 上若已创建站点 **BlogAPI**、绑定 **`http://*:8081:www.blogapi.com`**，且已按上文设置 **`web.config`**、**权限** 与 **hosts**，则 **`http://www.blogapi.com:8081/api/health`** 应返回 **`{"status":"ok","database":"ok"}`**（数据库配置正确时）。

换机器或改路径时，请重做 **§6、§7、§8**，并更新 **`hosts`/DNS**。
