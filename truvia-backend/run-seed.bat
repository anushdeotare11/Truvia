@echo off
cd /d "%~dp0"
call .venv\Scripts\python.exe -m scripts.seed_submit 74 6 45 > seed_submit.out.log 2>&1
