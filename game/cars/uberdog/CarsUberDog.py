"""
The Cars Uber Distributed Object Globals server.
"""

from direct.directnotify.DirectNotifyGlobal import directNotify

from game.cars.ai.CarsAIMsgTypes import (SHARDMANAGER_REGISTER_SHARD,
                                         SHARDMANAGER_UPDATE_SHARD)
from game.cars.distributed.CarsGlobals import *
from game.otp.ai.AIDistrict import AIDistrict
from game.otp.distributed.OtpDoGlobals import OTP_DO_ID_CARS_HOLIDAY_MANAGER
from game.otp.uberdog.UberDog import UberDog


class CarsUberDog(UberDog):
    notify = directNotify.newCategory("UberDog")

    def __init__(
            self, mdip, mdport, esip, esport, dcFilenames,
            serverId, minChannel, maxChannel):
        assert self.notify.debugStateCall(self)

        UberDog.__init__(
            self, mdip, mdport, esip, esport, dcFilenames,
            serverId, minChannel, maxChannel)

    def createObjects(self):
        UberDog.createObjects(self)

        # Ask for the ObjectServer so we can check the dc hash value
        context = self.allocateContext()
        self.queryObjectAll(self.serverId, context)

        self.holidayManager = self.generateGlobalObject(OTP_DO_ID_CARS_HOLIDAY_MANAGER, "HolidayManager")
        self.shardManager = self.generateGlobalObject(OTP_DO_ID_CARS_SHARD_MANAGER, "ShardManager")

    def handlePlayGame(self, msgType, di):
        # Handle Cars specific message types before
        # calling the base class
        if msgType == SHARDMANAGER_REGISTER_SHARD:
            self.shardManager.handleRegister(di)
        elif msgType == SHARDMANAGER_UPDATE_SHARD:
            self.shardManager.handleUpdate(di)
        else:
            AIDistrict.handlePlayGame(self, msgType, di)
