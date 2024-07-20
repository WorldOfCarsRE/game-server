cd ../../config

screen -dmS OTP "../../OtpGo/otpgo" otp.yml

sleep 5
# screen -dmS UberDOG python3 -m otp.uberdog

cd ..
screen -dmS Districts python3 -m DistrictStarter
