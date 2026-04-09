@echo off
chcp 65001 >nul
where winget >nul 2>&1
if errorlevel 1 (
  echo 未找到 winget。请手动打开浏览器安装 Python:
  echo https://www.python.org/downloads/
  start https://www.python.org/downloads/
  pause
  exit /b 1
)

echo 将使用 winget 安装 Python 3.12（可能需要你点「是」授权）。
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
echo.
echo 安装结束后请：关闭所有终端窗口 → 重新打开 → 双击 backend\setup-venv.bat → 再双击 run-backend.bat
pause
