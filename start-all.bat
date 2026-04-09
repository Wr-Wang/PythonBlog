@echo off
chcp 65001 >nul
echo 将打开两个窗口：请先等「后端」窗口出现 Uvicorn running / Application startup complete，再刷新浏览器。
echo.
start "Blog-后端-8000" cmd /k "%~dp0run-backend.bat"
timeout /t 3 /nobreak >nul
start "Blog-前端-Vite" cmd /k "%~dp0run-frontend.bat"
echo.
echo 已启动。请用浏览器打开（不要用 localhost，请用 127.0.0.1）：
echo   后端自检: http://127.0.0.1:8000/api/health
echo   前端开发: http://127.0.0.1:5173 （若端口被占用请看「前端」窗口里的实际地址）
echo.
pause
