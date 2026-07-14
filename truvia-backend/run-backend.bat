@echo off
cd /d "C:\Users\anush\Desktop\Truvia\truvia-backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info > srv.out.log 2>&1
