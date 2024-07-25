@echo off
title World of Cars Online - OTP Server
cd ../../config

:main
"../otpd/otpgo" otp.yml
pause
goto :main
