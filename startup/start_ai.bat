@echo off
title AI Server
cd ..
set /P PYTHON_PATH=<PYTHON_PATH

:main
%PYTHON_PATH% -m ai.AIStart
pause
goto :main