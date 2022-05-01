# Dialga

Dialga is a Python 3 asyncio-based OTP for World of Cars Online.

The base of this project is [here](https://github.com/alexanderr/OpenOTP).

## Python Dependencies
* [pydc](https://github.com/alexanderr/pydc)
* [lark](https://github.com/lark-parser/lark)
* [uvloop](https://github.com/MagicStack/uvloop) (optional)
* aiohttp

## Database Backends
Currently only MySQL and MongoDB is supported.

More database backends may be added in the future.

## How to setup:
* The OTP cluster can be ran through the `otp.otp` module.
* The AI server can be ran through the `ai.AIStart` module.

### Contributing
* Use 4 spaces instead of tabs.
* Do NOT use underscores in function names.
* The first word in a variable is lowercase for code functions. (testVar = 1)
* Make sure there are no trailing spaces in your code.
* Do NOT use underscores for variables and argument names. (test_var = 1)
* Do NOT do this with the equal sign. (testVar=1)
* Please test code before pushing.