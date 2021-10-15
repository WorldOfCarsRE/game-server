@echo off
cd ..
set /P PYTHON_PATH=<PYTHON_PATH

:main
%PYTHON_PATH% -m otp.otp
pause
goto :main