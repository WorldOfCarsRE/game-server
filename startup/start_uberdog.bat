@echo off
title UberDOG
cd ..
set /P PYTHON_PATH=<PYTHON_PATH

:main
%PYTHON_PATH% -m otp.uberdog
pause
goto :main
