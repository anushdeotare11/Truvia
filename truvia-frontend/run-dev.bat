@echo off
cd /d "%~dp0"
node .\node_modules\next\dist\bin\next dev -p 3000 > devd.out.log 2>&1
