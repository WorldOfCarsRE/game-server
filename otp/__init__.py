from par import parse_par_file
import os, builtins

config = parse_par_file('etc/local.par')

builtins.USE_ENC_TOKENS = os.path.isfile('etc/secret.par')

secretsData = None

if os.path.isfile('etc/secret.par'):
    secretsData = parse_par_file('etc/secret.par')

if config['General.UVLOOP']:
    import uvloop
    uvloop.install()
