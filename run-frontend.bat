@echo off
chcp 65001 >nul
cd /d "%~dp0frontend"
echo 当前目录: %CD%
echo.

where node >nul 2>&1
if errorlevel 1 (
  echo [错误] 未检测到 Node.js。请安装 LTS: https://nodejs.org/
  pause
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [错误] 未检测到 npm。
  pause
  exit /b 1
)

if not exist "node_modules" (
  echo 首次运行，正在 npm install ...
  call npm install
  if errorlevel 1 (
    pause
    exit /b 1
  )
)

echo ============================================================
echo  前端开发服务将启动（默认 http://127.0.0.1:5173）
echo  若端口被占用，终端会显示实际地址，请以终端为准。
echo  需先启动 run-backend.bat，否则页面里接口会失败。
echo  请勿关闭本窗口。
echo ============================================================
echo.

call npm run dev
echo.
pause
