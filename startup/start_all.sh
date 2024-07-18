cd ../config

export DEBUG=DBSS
screen -dmS OTP "../../OtpGo/otpgo" otp.yml

sleep 5
# screen -dmS UberDOG python3 -m otp.uberdog

cd ..
screen -dmS AI python3 -m game.cars.ai.AIStart config/config.prc
