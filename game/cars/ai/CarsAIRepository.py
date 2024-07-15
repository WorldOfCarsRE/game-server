from direct.directnotify import DirectNotifyGlobal
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator

from game.cars.ai.CarsAIMsgTypes import *
from game.otp.ai.AIDistrict import AIDistrict

from game.cars.distributed.CarsDistrictAI import CarsDistrictAI

class CarsAIRepository(AIDistrict):
    notify = DirectNotifyGlobal.directNotify.newCategory("CarsAIRepository")

    def __init__(self, *args, **kw):
        AIDistrict.__init__(self, *args, **kw)

    def getGameDoId(self):
        return OTP_DO_ID_CARS

    def createObjects(self):
        # Create a new district (aka shard) for this AI:
        self.district = CarsDistrictAI(self, self.districtName)
        self.district.generateOtpObject(
                OTP_DO_ID_CARS, OTP_ZONE_ID_DISTRICTS,
                doId=self.districtId)

        # mark district as enabled
        # NOTE: Only setEnabled is used in the client
        # instead of setAvailable.
        self.district.b_setEnabled(1)

        self.notify.info("Ready!")

    def registerShard(self):
        dg = PyDatagram()
        dg.addServerHeader(OTP_DO_ID_CARS_SHARD_MANAGER, self.ourChannel, SHARDMANAGER_REGISTER_SHARD)
        dg.addUint32(self.districtId)
        dg.addString(self.districtName)
        self.send(dg)

        # Set up the delete message as a post remove
        dg = PyDatagram()
        dg.addServerHeader(OTP_DO_ID_CARS_SHARD_MANAGER, self.ourChannel, SHARDMANAGER_DELETE_SHARD)
        self.addPostSocketClose(dg)

    def updateShard(self):
        dg = PyDatagram()
        dg.addServerHeader(OTP_DO_ID_CARS_SHARD_MANAGER, self.ourChannel, SHARDMANAGER_UPDATE_SHARD)
        dg.addUint16(self.getPopulation())
        dg.addUint8(self.district.getEnabled())
        self.send(dg)

    def incrementPopulation(self):
        AIDistrict.incrementPopulation(self)
        self.updateShard()

    def decrementPopulation(self):
        AIDistrict.decrementPopulation(self)
        self.updateShard()
