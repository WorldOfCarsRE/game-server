import builtins

class game:
    name = "cars"
    process = "ai"
builtins.game = game()

# NOTE: this file is not used in production. See AIServiceStart.py

import time
import os
import sys
import platform

print("Initializing...")

from panda3d.core import loadPrcFile

# Load our base configuration.
loadPrcFile(''.join(sys.argv[1:]))

if os.path.exists('config/local.prc'):
    # A local configuration exists, load it.
    loadPrcFile('config/local.prc')

from game.otp.ai.AIBaseGlobal import *
from . import CarsAIRepository
from direct.showbase import PythonUtil

# Clear the default model extension for AI developers, so they'll know
# when they screw up and omit it.
from pandac.PandaModules import loadPrcFileData
loadPrcFileData("AIStart.py", "default-model-extension")

simbase.mdip = ConfigVariableString("msg-director-ip", "127.0.0.1").getValue()

# Now the AI connects directly to the state server instead of the msg director
simbase.mdport = ConfigVariableInt("msg-director-port", 6666).getValue()

simbase.esip = ConfigVariableString("event-server-ip", "127.0.0.1").getValue()
simbase.esport = ConfigVariableInt("event-server-port", 4343).getValue()

districtType = 0
serverId = ConfigVariableInt("district-ssid", 20100000).getValue()

for i in range(1, 20+1):
    # always set up for i==1, then take the first district above 1 (if any)
    if i==1 or os.getenv("want_district_%s" % i):
        if i==1:
            postfix = ''
        else:
            postfix = '-%s' % i
        districtNumber = ConfigVariableInt(
            "district-id%s"%postfix,
            200000000 + i*1000000).getValue()
        districtName = ConfigVariableString(
            "district-name%s"%postfix,
            {
                1: 'Alignment'
            }.get(i, str(i))
        ).getValue()

        if platform.system() == "Windows":
            os.system(f"title World of Cars Online - AI ({districtName})")

        districtMinChannel = ConfigVariableInt(
            "district-min-channel%s"%postfix,
            200100000 + i*1000000).getValue()
        districtMaxChannel = ConfigVariableInt(
            "district-max-channel%s"%postfix,
            200149999 + i*1000000).getValue()
        if i != 1:
            break

print("-"*30, "creating cars district %s" % districtNumber, "-"*30)

simbase.air = CarsAIRepository.CarsAIRepository(
        simbase.mdip,
        simbase.mdport,
        simbase.esip,
        simbase.esport,
        None,
        districtNumber,
        districtName,
        districtType,
        serverId,
        districtMinChannel,
        districtMaxChannel)

# How we let the world know we are not running a service
simbase.aiService = 0

try:
    simbase.air.fsm.request("districtReset")
    run()
except:
    info = PythonUtil.describeException()
    simbase.air.writeServerEvent('ai-exception', districtNumber, info)
    raise
