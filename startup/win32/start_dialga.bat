@echo off
title World of Cars Online - OTP Server
cd ../../config

:main
set DEBUG=*
"../otpd/otpgo" otp.yml
pause
goto :main
