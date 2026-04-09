@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

cd /d "%~dp0backend"
echo 当前目录: %CD%
echo.

if not exist ".env" (
  echo [提示] 未找到 backend\.env。请复制 backend\.env.example 为 backend\.env 并填写 DATABASE_URL（SQL Server）。
  echo.
)

REM 1) 优先使用本仓库 venv（不依赖系统 PATH）
if exist "%CD%\venv\Scripts\python.exe" (
  set "PY=%CD%\venv\Scripts\python.exe"
  echo 使用虚拟环境: !PY!
  goto :have_py
)

REM 2) 系统 Python
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"

if not defined PY (
  echo [错误] 未检测到 Python。
  echo 请从 https://www.python.org/downloads/ 安装 3.10+，安装时勾选 "Add python.exe to PATH"。
  echo 或先双击运行 backend\setup-venv.bat 创建 venv。
  echo.
  pause
  exit /b 1
)

:have_py
echo 使用命令: %PY%
%PY% -c "import sys; print('Python:', sys.version); print('路径:', sys.executable)" 2>nul
if errorlevel 1 (
  echo [错误] Python 无法运行。
  pause
  exit /b 1
)

%PY% -c "import sys; exit(0 if 'WindowsApps' not in sys.executable else 1)" 2>nul
if errorlevel 1 (
  echo [错误] 当前是 Microsoft Store 占位 Python，无法安装依赖。请从 python.org 安装正式版，或运行 backend\setup-venv.bat。
  pause
  exit /b 1
)

echo.
echo 检查依赖 uvicorn ...
%PY% -c "import uvicorn" 2>nul
if errorlevel 1 (
  echo 正在安装依赖: pip install -r requirements.txt
  %PY% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [错误] pip 安装失败。
    pause
    exit /b 1
  )
)

echo.
echo ============================================================
echo  后端监听 0.0.0.0:8000（本机请用下面 IPv4 地址打开）
echo  测试页: http://127.0.0.1:8000/api/health
echo  API 文档: http://127.0.0.1:8000/docs
echo.
echo  请勿使用 http://localhost:8000 — 部分电脑会走 IPv6 导致拒绝连接，请用 127.0.0.1。
echo  请勿关闭本窗口，否则浏览器会显示「拒绝连接」。
echo ============================================================
echo.

REM 0.0.0.0: 本机 IPv4 与局域网均可；避免只绑 127.0.0.1 时偶发问题
%PY% -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo 服务已退出。若曾报错，请把上方完整输出复制保存。
pause
