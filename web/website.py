from otp import config

from aiohttp import web
from pymongo import MongoClient

from Crypto.Cipher import AES

import asyncio, hashlib, logging, json, os, time, binascii

SECRET = bytes.fromhex(config['General.LOGIN_SECRET'])

logging.basicConfig(level=logging.DEBUG)

DEFAULT_ACCOUNT = {
    'ACCOUNT_AV_SET': [0] * 6,
    'pirateAvatars': [0],
    'HOUSE_ID_SET': [0] * 6,
    'ESTATE_ID': 0,
    'ACCOUNT_AV_SET_DEL': [],
    'PLAYED_MINUTES': 0,
    'PLAYED_MINUTES_PERIOD': 0,
    'CREATED': time.ctime(),
    'LAST_LOGIN': time.ctime(),
}

DIR = config['WebServer.CONTENT_DIR']
PATCHER_VER_FILE = os.path.join(DIR, 'patcher.ver')
PATCHER_STARTSHOW_FILE = os.path.join(DIR, 'patcher.startshow')
HOST = config['WebServer.HOST']
PORT = config['WebServer.PORT']

if config['WebServer.WRITE_PATCH_FILES']:
    print('Writing patcher files...')
    from . import patcher

    with open(PATCHER_VER_FILE, 'w+') as f:
        f.write(patcher.PATCHER_VER)
    with open(PATCHER_STARTSHOW_FILE, 'w+') as f:
        f.write(patcher.PATCHER_STARTSHOW)

async def handle_patcher(request):
    print(request.method, request.path, request.query_string)
    return web.FileResponse(PATCHER_VER_FILE)

async def handle_start_show(request):
    print(request.method, request.path, request.query_string)

    return web.FileResponse(PATCHER_STARTSHOW_FILE)

with open(os.path.join(DIR, 'twhitelist.dat'), 'r', encoding='windows-1252') as f:
    WHITELIST = f.read()

async def handle_whitelist(request):
    print(request.method, request.path, request.query_string)
    return web.Response(text=WHITELIST)

# BUTTON_2: TOP TOONS
# BUTTON_3: PLAYER'S GUIDE
# BUTTON_4: HOMEPAGE
# BUTTON_5: MANAGE ACCOUNT
# BUTTON_7: FORGOT PASSWORD
# BUTTON_8: NEW ACCOUNT
#

import re

username_pattern = re.compile(r'[A-Za-z0-9_]+')
password_pattern = re.compile(r'[A-Za-z0-9_!@#$%^&*]+')

async def handle_login(request):
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
        info = await create_new_account(username, password, pool)

    print(info['salt'])

    cmp_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), info['salt'].encode(), 10000)

    if cmp_hash != binascii.a2b_base64(info['hash']):
        print('hashes dont match', cmp_hash, info['hash'], len(info['hash']))
        data = {
            'message': 'Incorrect password.'
        }
        return web.json_response(data)

    del info['hash']
    del info['salt']
    del info['_id']

    print('info', info)

    # Now make the token.

    cipher = AES.new(SECRET, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(json.dumps(info).encode('utf-8'))
    token = b''.join([cipher.nonce, tag, ciphertext])

    print(token)

    action = 'LOGIN_ACTION=PLAY'
    token = f'{token.hex()}'
    username = f'{username}'
    disl_id = f'GAME_DISL_ID={info["disl_id"]}'
    download_url = f'PANDA_DOWNLOAD_URL=http://{HOST}:{PORT}/'
    account_url = f'ACCOUNT_SERVER=http://{HOST}:{PORT}/'
    is_test_svr = 'IS_TEST_SERVER=0'
    game_url = f'GAME_SERVER={config["ClientAgent.HOST"]}'
    acc_params = f'webAccountParams=&chatEligible=1&secretsNeedsParentPassword=0'
    whitelist_url = f'GAME_WHITELIST_URL=http://{HOST}:{PORT}'

    response = {
        'token': token,
        'message': f'Welcome back, {username}.'
    }

    print('sending reponse', response)

    return web.json_response(response)

async def create_new_account(username: str, password: str, cursor: MongoClient):
    salt = binascii.b2a_base64(hashlib.sha256(os.urandom(60)).digest()).strip()
    accHash = binascii.b2a_base64(hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 10000)).strip().decode()

    try:
        data = {}
        data['class_name'] = 'Account'
        data['do_id'] = cursor.objects.count() + 1
        cursor.objects.insert_one(data)
        print('inserted')

        print('CREATED NEW ACCOUNT WITH ID: %s' % data['do_id'])

        array = (0).to_bytes(4, 'little') * 6
        av_set = len(array).to_bytes(2, 'little') + array

        fields = list(DEFAULT_ACCOUNT.items())

        cmdData = {}

        cmdData['do_id'] = data['do_id']
        cmdData['DcObjectType'] = 'Account'

        for field in fields:
            fieldName = field[0]
            cmdData[fieldName] = field[1]

        cursor.Account.insert_one(cmdData)

        acc = {}
        acc['username'] = username
        acc['hash'] = accHash
        acc['salt'] = salt.decode()
        acc['disl_id'] = data['do_id']
        acc['access'] = 'FULL'
        acc['account_type'] = 'NO_PARENT_ACCOUNT'
        acc['create_friends_with_chat'] = 'YES'
        acc['chat_code_creation_rule'] = 'YES'
        acc['whitelist_chat_enabled'] = 'YES'

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

    # TODO: Mongo.
    info = False

    if not info:
        return web.Response()

    cmp_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), info['salt'], iterations=101337)

    if cmp_hash != info['hash']:
        print('hashes dont match', cmp_hash, info['hash'], len(info['hash']))
        return web.Response(text='ACCOUNT SERVER RESPONSE\n\nerrorCode=20\nerrorMsg=bad password')

    return web.Response(text='ACCOUNT SERVER RESPONSE')

async def init_app():
    app = web.Application()
    app.router.add_get('/patcher.ver', handle_patcher)
    app.router.add_get('/launcher/current/patcher.ver', handle_patcher)
    app.router.add_get('/twhitelist.dat', handle_whitelist)

    app.router.add_get('/launcher/current/patcher.startshow', handle_start_show)

    app.router.add_post('/login', handle_login)
    app.router.add_static('/', path=config['WebServer.CONTENT_DIR'], name='releaseNotes.html')

    app.router.add_post('/api/authDelete', handle_auth_delete)

    pool = MongoClient('127.0.0.1:27017')['Dialga']
    app['pool'] = pool

    print('init done')

    return app

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app())
    print('running app..')
    web.run_app(app, host=HOST, port=PORT)
    app['pool'].terminate()