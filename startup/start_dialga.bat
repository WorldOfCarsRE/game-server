@echo off
title OTP Server
cd ../config

:main
"../otpd/otpgo" otp.yml
pause
goto :main
