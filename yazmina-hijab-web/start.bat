@echo off
chcp 65001 >nul 2>&1
title Yazmina Hijab Web

echo ============================================
echo   Yazmina Hijab Web — Starting...
echo ============================================
echo.

cd /d "%~dp0"

:: ── Step 1: Check Python ──────────────────────────────────────────
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo     [FAIL] Python not found. Install Python 3.11+ and add to PATH.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo     %%i

:: ── Step 2: Install backend dependencies ──────────────────────────
echo [2/5] Checking backend dependencies...
cd backend
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo     Installing backend dependencies...
    pip install -r requirements.txt -q
)
echo     Backend deps OK.
cd ..

:: ── Step 3: Setup database + admin ────────────────────────────────
echo [3/5] Setting up database...
cd backend
python setup_dev.py --auto
cd ..

:: ── Step 4: Check frontend ───────────────────────────────────────
echo [4/5] Checking frontend...
cd frontend
if not exist "node_modules" (
    echo     Installing frontend dependencies...
    call npm install
)
if not exist "node_modules\vite\dist\node\cli.js" (
    echo     Vite dist missing, reinstalling...
    call npm cache clean --force
    rmdir /s /q node_modules 2>nul
    call npm install
)
echo     Frontend deps OK.
cd ..

:: ── Step 5: Start servers ────────────────────────────────────────
echo [5/5] Starting servers...
echo.

:: Start backend in new window
echo     Starting backend on http://localhost:8765 ...
start "Yazmina Backend" cmd /k "cd /d %~dp0backend && uvicorn app.main:app --reload --port 8765"

:: Wait a moment for backend to start
timeout /t 2 /nobreak >nul

:: Start frontend in new window
echo     Starting frontend on http://localhost:5173 ...
start "Yazmina Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================
echo   Both servers started!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8765
echo   API Docs: http://localhost:8765/docs
echo ============================================
echo.
echo   Press any key to open browser...
pause >nul

start http://localhost:5173
