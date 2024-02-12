@echo off
title OTP Server
cd ../config

:main
"../otpd/otpgo" -l info otp.yml
pause
goto :main
