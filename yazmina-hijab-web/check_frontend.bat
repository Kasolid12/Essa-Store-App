@echo off
chcp 65001 >nul 2>&1

echo === Yazmina Hijab Web - Frontend Check ===
echo.

cd /d "%~dp0frontend"
echo Current dir: %CD%
echo.

echo [1] Checking node_modules...
if not exist "node_modules" (
    echo     node_modules NOT FOUND - running npm install...
    call npm install
    if errorlevel 1 (
        echo     [FAIL] npm install failed
        pause
        exit /b 1
    )
)

echo [2] Checking vite/dist...
if not exist "node_modules\vite\dist\node\cli.js" (
    echo     vite/dist MISSING - reinstalling...
    call npm cache clean --force
    rmdir /s /q node_modules 2>nul
    call npm install
    if errorlevel 1 (
        echo     [FAIL] npm reinstall failed
        pause
        exit /b 1
    )
)

echo [3] Checking vite version...
call npx vite --version
if errorlevel 1 (
    echo     [FAIL] vite not working
    pause
    exit /b 1
)

echo.
echo [OK] Frontend environment is ready!
echo Run: npm run dev
echo.
pause
