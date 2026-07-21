@echo off
cd /d "%~dp0"
call .venv\Scripts\python.exe -m scripts.cluster_rings > cluster_rings.out.log 2>&1
