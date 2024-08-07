cd ../../config

screen -dmS OTP "../../OtpGo/otpgo" otp.yml

cd ..
screen -dmS Districts python3 -m DistrictStarter
