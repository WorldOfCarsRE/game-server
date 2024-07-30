"""
Start the Cars UberDog (Uber Distributed Object Globals server).
"""

import builtins

class game:
    name = "uberDog"
    process = "server"
builtins.game = game()

from game.otp.uberdog.UberDogGlobal import *
from game.cars.uberdog.CarsUberDog import CarsUberDog

from panda3d.core import loadPrcFile, ConfigVariableString
import sys, os

# Load our base configuration.
loadPrcFile(''.join(sys.argv[1:]))

if os.path.exists('config/local.prc'):
    # A local configuration exists, load it.
    loadPrcFile('config/local.prc')

print("Initializing the Cars UberDog (Uber Distributed Object Globals server)...")

uber.mdip = ConfigVariableString("msg-director-ip", "127.0.0.1").getValue()
uber.mdport = ConfigVariableInt("msg-director-port", 6666).getValue()

uber.esip = ConfigVariableString("event-server-ip", "127.0.0.1").getValue()
uber.esport = ConfigVariableInt("event-server-port", 4343).getValue()

stateServerId = ConfigVariableInt("state-server-id", 20100000).getValue()

uber.objectNames = set(os.getenv("uberdog_objects", "").split())

minChannel = ConfigVariableInt("uberdog-min-channel", 200400000).getValue()
maxChannel = ConfigVariableInt("uberdog-max-channel", 200449999).getValue()

uber.air = CarsUberDog(
        uber.mdip, uber.mdport,
        uber.esip, uber.esport,
        None,
        stateServerId,
        minChannel,
        maxChannel)

# How we let the world know we are not running a service
uber.aiService = 0

try:
    run()
except:
    info = describeException()
    #uber.air.writeServerEvent('uberdog-exception', districtNumber, info)
    raise

