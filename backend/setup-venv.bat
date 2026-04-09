@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"

if not defined PY (
  echo [错误] 未找到 Python。请从 https://www.python.org/downloads/ 安装并勾选 Add to PATH。
  pause
  exit /b 1
)

echo 使用: %PY%
%PY% -c "import sys; sys.exit(0 if 'WindowsApps' not in sys.executable else 1)" 2>nul
if errorlevel 1 (
  echo [错误] 当前为 Microsoft Store 占位 Python。请从 https://www.python.org/downloads/ 安装正式版并勾选 Add to PATH。
  pause
  exit /b 1
)

if exist "venv\Scripts\python.exe" (
  echo 已存在 venv，跳过创建。
) else (
  echo 正在创建虚拟环境 venv ...
  %PY% -m venv venv
  if errorlevel 1 (
    pause
    exit /b 1
  )
)

echo 正在安装依赖 ...
call venv\Scripts\python.exe -m pip install -U pip
call venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  pause
  exit /b 1
)

echo.
echo 完成。以后请运行项目根目录的 run-backend.bat（会优先使用本目录下的 venv）。
pause
