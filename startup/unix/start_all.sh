cd ../../config

screen -dmS OTP "../../OtpGo/otpgo" otp.yml >otpgo.log 2>&1

cd ..
screen -dmS Districts python3 -m DistrictStarter
