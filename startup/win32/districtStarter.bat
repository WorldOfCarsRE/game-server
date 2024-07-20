@echo off
cd ../..

title %DISTRICT_NAME%

set /P PYTHON_PATH=<PYTHON_PATH

:main
%PYTHON_PATH% -m game.cars.ai.AIServiceStart --mdip=127.0.0.1 --mdport=6666 --logpath=logs/ --district_number=%BASE_CHANNEL% --district_name="%DISTRICT_NAME%" --ssid=20100000 --min_objid=%MIN_OBJ_ID% --max_objid=%MAX_OBJ_ID%
pause
goto :main
