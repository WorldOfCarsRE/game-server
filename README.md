# Dialga

Dialga is a Python 3 asyncio-based OTP for the Sunrise Toontown Online 2013 client.

The goal of this project is to be a Astron replacement to play Disney's Toontown Online.

The AI server is rewritten from scratch to take advantage of Python 3 features and allow the code to be more readable.

The base of this project is [here](https://github.com/alexanderr/OpenOTP).

## Python Dependencies
* [lark](https://github.com/lark-parser/lark)
* [uvloop](https://github.com/MagicStack/uvloop) (optional)
* aiohttp

## Database Backends
Currently only MongoDB is supported.

More database backends may be added in the future.

## How to setup:
* The OTP cluster can be ran through the `otp.otp` module.
* The AI server can be ran through the `ai.AIStart` module.
* The python web server can be ran through the `web.website` module. This is required for authentication.