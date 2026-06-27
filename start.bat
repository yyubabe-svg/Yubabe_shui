@echo off
chcp 65001 >nul
title 蜀水智库 AI

cd /d "%~dp0"

echo ========================================
echo   蜀水智库 AI 启动中...
echo ========================================
echo.

REM 检查Python虚拟环境
if not exist "backend\venv" (
    echo 📦 首次运行，正在创建Python虚拟环境...
    cd backend
    python -m venv venv
    call venv\Scripts\activate.bat
    echo 📦 正在安装依赖（首次需要几分钟）...
    pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings python-multipart python-docx aiofiles python-dotenv httpx numpy -q
    cd ..
    echo ✅ 依赖安装完成
    echo.
)

REM 启动后端
echo 🚀 启动服务...
cd backend
call venv\Scripts\activate.bat

echo.
echo ========================================
echo   ✅ 蜀水智库 AI 已启动！
echo.
echo   本机访问:  http://localhost:8000
echo   局域网访问: 请查看本机IP地址
echo.
echo   API文档:  http://localhost:8000/docs
echo.
echo   按 Ctrl+C 停止服务
echo ========================================
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
