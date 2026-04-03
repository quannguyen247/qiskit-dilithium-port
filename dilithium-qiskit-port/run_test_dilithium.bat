@echo off
REM ====================================================================
REM  Quantum Dilithium JS ↔ Python Authentication Test Runner
REM  Platform: Windows (Batch)
REM ====================================================================

setlocal enabledelayedexpansion

echo.
echo ====================================================================
echo   QUANTUM DILITHIUM AUTHENTICATION TEST (JSON-based Protocol)
echo     Board Client (LyCheeRVnano) ↔ Python Server
echo ====================================================================
echo.

REM Check if Python is installed
where python >nul 2>nul
if errorlevel 1 (
    echo ❌ ERROR: Python not found!
    echo    Please install Python from: https://python.org/
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=*" %%a in ('python --version') do set PYTHON_VERSION=%%a

echo ✅ Python detected: %PYTHON_VERSION%
echo.

echo ====================================================================
echo  PHASE 1: PREPARE ENVIRONMENT
echo ====================================================================
echo.

REM Check if data files already exist (do NOT delete - wait for alice_client.js)
if exist "data/publickey.json" (
    echo ✅ publickey.json already exists (from board client)
) else (
    echo ⚠️  publickey.json NOT FOUND
)

if not exist "data" (
    mkdir data
    echo 📁 Created ./data directory
)

echo.
echo ✅ Environment ready
echo.

echo ====================================================================
echo  PHASE 2: WAIT FOR BOARD CLIENT
echo ====================================================================
echo.
echo 📋 IMPORTANT: Open Terminal 2 and run:
echo    node alice_client.js
echo.
echo This will generate:
echo    ✓ ./data/publickey.json (random from board KeyGen)
echo    ✓ After server creates challenge.json
echo    ✓ ./data/signature.json (after board signs)
echo.
echo Once publickey.json exists, press any key to continue...
echo.

REM Wait for publickey.json to be created by alice_client.js
:wait_for_publickey
if exist "data/publickey.json" (
    goto found_publickey
)
timeout /t 2 /nobreak >nul
goto wait_for_publickey

:found_publickey
echo ✅ publickey.json detected!
echo.

echo ====================================================================
echo  PHASE 3: SERVER - RUNNING TEST (JSON Protocol)
echo ====================================================================
echo.

REM Run Python server (Quantum version with Qiskit)
python run_test_dilithium_quantum.py

if errorlevel 1 (
    echo ❌ ERROR: Server verification failed!
    pause
    exit /b 1
)

echo ====================================================================
echo  PHASE 4: RESULTS
echo ====================================================================
echo.

REM Display file contents
echo [GENERATED FILES]
echo.

if exist "data/publickey.json" (
    echo ✅ ./data/publickey.json (JSON)
)

if exist "data/challenge.json" (
    echo ✅ ./data/challenge.json (JSON)
)

if exist "data/signature.json" (
    echo ✅ ./data/signature.json (JSON)
)

if exist "data/verification_result.json" (
    echo ✅ ./data/verification_result.json (JSON)
)

echo.
echo ====================================================================
echo ✅ AUTHENTICATION WORKFLOW COMPLETE!
echo ====================================================================
echo.
echo 📚 For more details, see: WORKFLOW_JS_PYTHON.md
echo.

pause
