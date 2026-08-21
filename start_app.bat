@echo off
REM ============================================================
REM  YAZMINA HIJAB - LAUNCHER APLIKASI (Windows)
REM  ------------------------------------------------------------
REM  Cara PALING aman membuka aplikasi: double-click file INI,
REM  BUKAN main.py.
REM
REM  Mengapa? Double-click main.py memakai Python bawaan Windows
REM  (sering versi berbeda) yang BELUM tentu punya dependensi
REM  cloud (psycopg2), sehingga auto-sync gagal dan tombol SYNC
REM  NOW jadi non-aktif (status cloud non-aktif, console log
REM  "no module psycopg2").
REM
REM  File launcher ini memakai python yang SAMA dengan terminal
REM  Anda: venv proyek bila ada, kalau tidak python di PATH.
REM  Lalu memeriksa dependensi sebelum menjalankan aplikasi.
REM ============================================================
setlocal
cd /d "%~dp0"
title Yazmina Hijab - Operations OS

REM --- Pilih interpreter: venv proyek bila ada, jika tidak python di PATH ---
set "PY=python"
if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"

echo.
echo  ============================================
echo    YAZMINA HIJAB - OPERATIONS OS
echo  ============================================
echo.

REM --- Mode pemeriksaan: start_app.bat --check -----------------
if /I "%~1"=="--check" goto :check

REM --- 1. Pastikan python bisa ditemukan -----------------------
if "%PY%"=="python" (
    where python >nul 2>&1
    if errorlevel 1 (
        echo  [ERROR] Perintah "python" tidak ditemukan di PATH.
        echo  Solusi:
        echo    - Install Python 3.11+ dari python.org dan centang
        echo      "Add python.exe to PATH", ATAU
        echo    - Buat virtual environment proyek:
        echo        python -m venv venv
        echo        venv\Scripts\activate
        echo        pip install -r requirements.txt
        goto :fail
    )
)

REM --- 2. Pastikan driver cloud (psycopg2) terpasang -----------
%PY% -c "import psycopg2" >nul 2>&1
if errorlevel 1 goto :no_psycopg2

REM --- 3. Tampilkan python yang dipakai & jalankan aplikasi ----
echo  [OK] Python yang dipakai:
%PY% -c "import sys; print('       ' + sys.executable)"
echo  [OK] Driver cloud (psycopg2) terpasang.
echo.
echo  Menjalankan aplikasi... (tutup jendela untuk keluar)
echo  ------------------------------------------------------------
%PY% main.py
set "APP_EXIT=%ERRORLEVEL%"

if not "%APP_EXIT%"=="0" (
    echo.
    echo  Aplikasi berhenti dengan kode error %APP_EXIT%.
    echo  Baca pesan error di atas, atau coba buka lewat terminal:
    echo      python main.py
)
exit /b %APP_EXIT%

:no_psycopg2
echo  [ERROR] Driver cloud (psycopg2) BELUM terpasang pada Python ini:
%PY% -c "import sys; print('       ' + sys.executable)"
echo.
echo  Inilah penyebab "no module psycopg2" saat double-click main.py:
echo  Windows membuka main.py memakai Python yang BERBEDA (tanpa
echo  psycopg2), sedangkan file launcher ini memakai python yang
echo  sama dengan terminal Anda.
echo.
echo  Solusi (jalankan di folder aplikasi ini):
echo      pip install psycopg2-binary
echo  atau install semua dependensi:
echo      pip install -r requirements.txt
goto :fail

:check
REM --- Hanya memeriksa lingkungan, tidak membuka aplikasi --------
if "%PY%"=="python" (
    where python >nul 2>&1
    if errorlevel 1 (
        echo  [CEK] python   : TIDAK DITEMUKAN di PATH
        goto :fail
    )
)
%PY% -c "import sys; print('[CEK] python   : ' + sys.executable)"
%PY% -c "import psycopg2; print('[CEK] psycopg2 : OK (' + psycopg2.__version__ + ')')" 2>nul || echo  [CEK] psycopg2 : TIDAK ADA
%PY% -c "import PySide6; print('[CEK] PySide6  : OK')" 2>nul || echo  [CEK] PySide6  : TIDAK ADA
echo.
echo  [CEK] Selesai.
exit /b 0

:fail
echo.
echo  Tekan tombol apa saja untuk menutup...
pause >nul
exit /b 1
