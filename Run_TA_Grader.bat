@echo off
:: Self-elevate to Administrator if not already running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"

:: Copilot OAuth is supported by the official SDK, not the OmniRoute API shim.
python -c "import copilot" >nul 2>&1
if errorlevel 1 (
    echo Installing GitHub Copilot SDK for TA Grader...
    python -m pip install github-copilot-sdk
    if errorlevel 1 (
        echo Failed to install github-copilot-sdk. Check Python 3.11+ and network access.
        pause
        exit /b 1
    )
)

:: Terminate any existing TA_Grader instances to prevent duplicate listeners
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*TA_Grader.py*' -and $_.ProcessId -ne $PID } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

python TA_Grader.py
