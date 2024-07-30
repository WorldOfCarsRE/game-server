@echo off
title World of Cars Online - UberDOG Server
cd ../..
set /P PYTHON_PATH=<PYTHON_PATH

:main
%PYTHON_PATH% -m game.cars.uberdog.Start config/config.prc
pause
goto :main
