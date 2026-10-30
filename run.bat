@echo off
setlocal enabledelayedexpansion
title FairLendAI - Explainable Credit Assessment Platform
cd /d "%~dp0"

echo ===============================================================================
echo   FairLendAI - Explainable Credit Assessment Platform Launcher
echo   B.Tech Capstone Project in Artificial Intelligence ^& Data Science
echo   Responsible AI ^| Document Intelligence ^| Explainability ^| Fairness Monitoring
echo ===============================================================================
echo.

:: 1. Priority: Existing Project Virtual Environment
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        echo [FairLendAI] Activating project virtual environment in .venv...
        ".venv\Scripts\python.exe" launcher.py %*
        if errorlevel 1 (
            echo.
            echo [FairLendAI Error] Application exited with error code !ERRORLEVEL!.
            pause
        )
        exit /b !ERRORLEVEL!
    )
)

:: 2. Try Windows 'py' launcher for Python 3.14, 3.13, 3.12
for %%V in (3.14 3.13 3.12) do (
    py -%%V -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        echo [FairLendAI] Launching via Windows py -%%V...
        py -%%V launcher.py %*
        if errorlevel 1 (
            echo.
            echo [FairLendAI Error] Application exited with error code !ERRORLEVEL!.
            pause
        )
        exit /b !ERRORLEVEL!
    )
)

:: 3. Fall back to Python on system PATH
python -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,14) else 1)" >nul 2>nul
if not errorlevel 1 (
    echo [FairLendAI] Launching via system Python on PATH...
    python launcher.py %*
    if errorlevel 1 (
        echo.
        echo [FairLendAI Error] Application exited with error code !ERRORLEVEL!.
        pause
    )
    exit /b !ERRORLEVEL!
)

:: 4. Diagnostic error if no compatible Python was detected
echo.
echo ===============================================================================
echo   [ERROR] Compatible 64-bit Python 3.12 - 3.14 was not found!
echo   Please ensure Python is installed and added to your system PATH.
echo ===============================================================================
echo.
pause
exit /b 1
