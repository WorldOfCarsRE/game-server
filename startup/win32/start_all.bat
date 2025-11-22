@echo off
taskkill /IM OtpGo.exe /F

cd /d "%~dp0"
start "" "%~dp0start_dialga.bat"
start "" "%~dp0start_uberdog.bat"
start "" "%~dp0start_ai.bat"
exit
