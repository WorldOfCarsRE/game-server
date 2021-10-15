@echo off
cd ..

:main
python -m web.website
pause
goto :main