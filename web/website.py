from otp import config

from aiohttp import web
from pymongo import MongoClient

from Crypto.Cipher import AES

from datetime import datetime

import asyncio, hashlib, logging, json, os, time, binascii

SECRET = bytes.fromhex(config['General.LOGIN_SECRET'])

logging.basicConfig(level = logging.DEBUG)

HOST = config['WebServer.HOST']
PORT = config['WebServer.PORT']

DEFAULT_ACCOUNT = {
    'ACCOUNT_AV_SET': [0] * 6,
    'pirateAvatars': [0],
    'HOUSE_ID_SET': [0] * 6,
    'ESTATE_ID': 0,
    'ACCOUNT_AV_SET_DEL': [],
    'PLAYED_MINUTES': 0,
    'PLAYED_MINUTES_PERIOD': 0,
    'CREATED': time.ctime(),
    'LAST_LOGIN': time.ctime()
}

import re

username_pattern = re.compile(r'[A-Za-z0-9_]+')
password_pattern = re.compile(r'[A-Za-z0-9_!@#$%^&*]+')

async def handleLogin(request):
    print(request.method, request.path, request.query)
    args = await request.post()

    username = args.get('u').lower()

    if not username:
        data = {
            'message': 'No username specified in request.'
        }
        return web.json_response(data)

    if not username_pattern.match(username):
        data = {
            'message': 'Username is not valid.'
        }
        return web.json_response(data)

    password = args.get('p')

    if not password:
        data = {
            'message': 'No password specified in request.'
        }
        return web.json_response(data)

    if not password_pattern.match(password):
        data = {
            'message': 'Password is not valid.'
        }
        return web.json_response(data)

    if len(username) > 255:
        data = {
            'message': 'Username is greater than 255 characters.'
        }
        return web.json_response(data)

    if len(password) > 255:
        data = {
            'message': 'Password is greater than 255 characters.'
        }
        return web.json_response(data)

    print(f'{username} attempting to login...')

    pool = request.app['pool']
    info = pool.accounts.find_one({'username': username})

    if not info:
        print(f'Creating new account for {username}...')
        info = await createNewAccount(username, password, pool)

    cmpHash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), info['salt'].encode(), 10000)

    if cmpHash != binascii.a2b_base64(info['hash']):
        print('hashes dont match', cmpHash, info['hash'], len(info['hash']))
        data = {
            'message': 'Incorrect password.'
        }
        return web.json_response(data)

    del info['hash']
    del info['salt']
    del info['_id']

    account = pool.Account.find_one({'_id': info['dislId']})

    info['accountDays'] = getAccountDays(account['CREATED'])

    # Now make the token.
    cipher = AES.new(SECRET, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(json.dumps(info).encode('utf-8'))
    token = b''.join([cipher.nonce, tag, ciphertext])

    token = f'{token.hex()}'

    response = {
        'token': token,
        'message': f'Welcome back, {username}.'
    }

    print('sending response', response)

    return web.json_response(response)

def getAccountDays(createdTime):
    # Retrieve the creation date.
    try:
        creationDate = datetime.fromtimestamp(time.mktime(time.strptime(createdTime)))
    except ValueError:
        creationDate = ''

    accountDays = -1

    if creationDate:
        now = datetime.fromtimestamp(time.mktime(time.strptime(time.ctime())))
        accountDays = abs((now - creationDate).days)

    return accountDays

async def generateObjectId(cursor: MongoClient):
    returnDoc = cursor.objects.find_one_and_update({'type': 'objectId'}, {'$inc': {'nextId': 1}})
    return returnDoc['nextId']

async def createNewAccount(username: str, password: str, cursor: MongoClient):
    salt = binascii.b2a_base64(hashlib.sha256(os.urandom(60)).digest()).strip()
    accHash = binascii.b2a_base64(hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 10000)).strip().decode()

    try:
        data = {}
        data['className'] = 'Account'
        data['_id'] = await generateObjectId(cursor)
        cursor.objects.insert_one(data)
        print('inserted')

        dislId = data['_id']
        print(f'CREATED NEW ACCOUNT WITH ID: {dislId}')

        fields = list(DEFAULT_ACCOUNT.items())

        cmdData = {}

        cmdData['_id'] = data['_id']
        cmdData['DcObjectType'] = 'Account'

        for field in fields:
            fieldName = field[0]
            cmdData[fieldName] = field[1]

        cursor.Account.insert_one(cmdData)

        acc = {}
        acc['username'] = username
        acc['hash'] = accHash
        acc['salt'] = salt.decode()
        acc['dislId'] = data['_id']
        acc['access'] = 'FULL'
        acc['accountType'] = 'NO_PARENT_ACCOUNT'
        acc['createFriendsWithChat'] = 'YES'
        acc['chatCodeCreationRule'] = 'YES'
        acc['whitelistChatEnabled'] = 'YES'

        cursor.accounts.insert_one(acc)
        return acc

    except Exception as e:
        print(e, e.__class__)

    return []

async def handle_auth_delete(request):
    print(request.method, request.path, request.query, request.headers)
    args = await request.post()
    username, password = args.get('n'), args.get('p')

    if not username:
        return web.Response()

    if not username_pattern.match(username):
        return web.Response()

    if not password:
        return web.Response()

    if not password_pattern.match(password):
        return web.Response()

    if len(username) > 255:
        return web.Response()

    if len(password) > 255:
        return web.Response()

    pool = request.app['pool']
    info = pool.accounts.find_one({'username': username})

    if not info:
        return web.Response()

    cmp_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), info['salt'].encode(), 10000)

    if cmp_hash != binascii.a2b_base64(info['hash']):
        print('hashes dont match', cmp_hash, info['hash'], len(info['hash']))
        return web.Response(text='ACCOUNT SERVER RESPONSE\n\nerrorCode=20\nerrorMsg=bad password')

    return web.Response(text='ACCOUNT SERVER RESPONSE')

async def init_app():
    app = web.Application()

    app.router.add_post('/login', handleLogin)

    pool = MongoClient(config['MongoDB.Host'])[config['MongoDB.Name']]
    app['pool'] = pool

    # Check if we need to create our initial entries in the database.
    entry = pool.objects.find_one({'type': 'objectId'})

    if entry is None:
        # We need to create our initial entry.
        pool.objects.insert_one({'type': 'objectId', 'nextId': config['DatabaseServer.MinRange']})

    print('init done')

    return app

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app())
    print('running app..')
    web.run_app(app, host = HOST, port = PORT)
    app['pool'].terminate()