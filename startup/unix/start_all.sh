cd ../../config

screen -dmS OTP "../../OtpGo/otpgo" otp.yml

cd ..
screen -dmS UberDOG python3 -m game.cars.uberdog.Start config/config.prc
screen -dmS Districts python3 -m DistrictStarter
