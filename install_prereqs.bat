@echo off
REM ============================================================
REM  Assignment 3 - Prerequisite installer (Windows 10/11)
REM  Run from your project folder as Administrator:
REM     right-click Command Prompt -> "Run as administrator"
REM     cd C:\path\to\btc-mlops
REM     install_prereqs.bat
REM ============================================================

REM --- Check for admin rights ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Please run this script as Administrator.
    pause
    exit /b 1
)

REM --- Check winget exists ---
where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] winget not found. Install "App Installer" from the Microsoft Store, then re-run.
    pause
    exit /b 1
)

set WG=winget install -e --silent --accept-package-agreements --accept-source-agreements --id

echo.
echo ===== 1/8 Enabling WSL2 (needed by Docker Desktop) =====
wsl --install --no-distribution

echo.
echo ===== 2/8 Installing Git =====
%WG% Git.Git

echo.
echo ===== 3/8 Installing Python 3.10 =====
%WG% Python.Python.3.10

echo.
echo ===== 4/8 Installing Docker Desktop =====
%WG% Docker.DockerDesktop

echo.
echo ===== 5/8 Installing kubectl =====
%WG% Kubernetes.kubectl

echo.
echo ===== 6/8 Installing Minikube =====
%WG% Kubernetes.minikube

echo.
echo ===== 7/8 Installing Helm =====
%WG% Helm.Helm

echo.
echo ===== 8/8 Creating Python virtual environment and installing libraries =====
REM The "py" launcher lives in C:\Windows, so it works without restarting cmd
py -3.10 -m venv .venv
if %errorlevel% neq 0 (
    echo [WARN] Could not create venv yet. Restart cmd and run the Python part again:
    echo        py -3.10 -m venv .venv
    echo        .venv\Scripts\activate
    echo        pip install -r requirements-dev.txt
    goto done
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install flask==3.0.3 gunicorn==22.0.0 pandas==2.2.2 numpy==1.26.4 ^
    scikit-learn statsmodels==0.14.2 xgboost joblib==1.4.2 yfinance requests ^
    kfp pytest flake8 black locust

REM Save the list so your partner can install the same versions
pip freeze > requirements-dev.txt

:done
echo.
echo ============================================================
echo  DONE. Now:
echo   1. RESTART your computer (WSL2 + Docker need it).
echo   2. Open Docker Desktop once and wait until it says "Engine running".
echo   3. Open a NEW cmd and verify:
echo        git --version
echo        python --version
echo        docker --version
echo        kubectl version --client
echo        minikube version
echo        helm version
echo   4. Start your cluster:
echo        minikube start --driver=docker --cpus=4 --memory=6g
echo        minikube addons enable ingress
echo        minikube addons enable metrics-server
echo   5. Each time you work on the project:
echo        .venv\Scripts\activate
echo ============================================================
pause
