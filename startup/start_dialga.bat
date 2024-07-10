@echo off
title OTP Server
cd ../config

:main
set DEBUG=DBSS
"../otpd/otpgo" otp.yml
pause
goto :main
