@echo off
cd ..
set /P PYTHON_PATH=<PYTHON_PATH

:main
%PYTHON_PATH% -m web.website
pause
goto :main