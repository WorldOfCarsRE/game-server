cd ..
screen -dmS OTP python3 -m otp.otp
sleep 5
screen -dmS UberDOG python3 -m otp.uberdog
screen -dmS AI python3 -m ai.AIStart
screen -dmS Web python3 -m web.website