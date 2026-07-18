@echo off
cd /d "%~dp0"
REM Free port 8000 if a previous instance is still bound, so restarting the
REM backend does not fail with [WinError 10048] "address already in use".
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%p >nul 2>&1
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 > backend.out.log 2>&1
