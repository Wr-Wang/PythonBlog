@echo off
chcp 65001 >nul
echo ================== 博客项目诊断 ==================
echo.

echo [1] 端口 8000 / 5173 / 1433（LISTENING 表示有服务在监听）
netstat -ano | findstr ":8000"
netstat -ano | findstr ":5173"
netstat -ano | findstr ":1433"
echo.

echo [2] Python
where py 2>nul
where python 2>nul
if exist "%~dp0backend\venv\Scripts\python.exe" (
  echo venv: %~dp0backend\venv\Scripts\python.exe
) else (
  echo 未发现 backend\venv
)
echo.

echo 若 8000 无 LISTENING，请先启动后端。1433 无 LISTENING 时检查本机 SQL Server 是否已启动并监听。
echo.
pause
