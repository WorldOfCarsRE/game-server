@echo off
title World of Cars Online - AI
cd ../..
set /P PYTHON_PATH=<PYTHON_PATH

:main
%PYTHON_PATH% -m game.cars.ai.AIStart config/config.prc
pause
goto :main
