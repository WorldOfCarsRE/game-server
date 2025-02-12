"""
The Cars Uber Distributed Object Globals server.
"""

from direct.directnotify.DirectNotifyGlobal import directNotify

from game.cars.ai.CarsAIMsgTypes import (SHARDMANAGER_REGISTER_SHARD,
                                         SHARDMANAGER_UPDATE_SHARD)
from game.cars.distributed.CarsGlobals import *
from game.otp.ai.AIDistrict import AIDistrict
from game.otp.distributed.OtpDoGlobals import OTP_DO_ID_CARS_HOLIDAY_MANAGER, OTP_DO_ID_CARS_SHARD_MANAGER, OTP_DO_ID_CARS
from game.otp.uberdog.UberDog import UberDog

from .ShardManagerUD import ShardManagerUD


class CarsUberDog(UberDog):
    notify = directNotify.newCategory("UberDog")

    def __init__(
            self, mdip, mdport, esip, esport, dcFilenames,
            serverId, minChannel, maxChannel):
        assert self.notify.debugStateCall(self)

        UberDog.__init__(
            self, mdip, mdport, esip, esport, dcFilenames,
            serverId, minChannel, maxChannel)

    def getGameDoId(self):
        return OTP_DO_ID_CARS

    def createObjects(self):
        UberDog.createObjects(self)

        # Ask for the ObjectServer so we can check the dc hash value
        context = self.allocateContext()
        self.queryObjectAll(self.serverId, context)

        self.holidayManager = self.generateGlobalObject(OTP_DO_ID_CARS_HOLIDAY_MANAGER, "HolidayManager")

        # ShardManager has to be an object on the state server because the game
        # expects some things (like the tutorial and yards) to generate as this object's
        # parent.
        self.shardManager = ShardManagerUD(self)
        # HACK: parentId has to be set as at least something to prevent message truncation.
        self.shardManager.generateWithRequiredAndId(OTP_DO_ID_CARS_SHARD_MANAGER, 1, 0)
        self.setAIReceiver(OTP_DO_ID_CARS_SHARD_MANAGER)

    # def handlePlayGame(self, msgType, di):
    #     # Handle Cars specific message types before
    #     # calling the base class
    #     if msgType == SHARDMANAGER_REGISTER_SHARD:
    #         self.shardManager.handleRegister(di)
    #     elif msgType == SHARDMANAGER_UPDATE_SHARD:
    #         self.shardManager.handleUpdate(di)
    #     else:
    #         AIDistrict.handlePlayGame(self, msgType, di)
