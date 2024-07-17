from direct.directnotify import DirectNotifyGlobal
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator

from game.cars.ai.CarsAIMsgTypes import *
from game.cars.distributed.CarsGlobals import *
from game.cars.zone import ZoneConstants

from game.otp.ai.AIDistrict import AIDistrict

from game.cars.distributed.CarsDistrictAI import CarsDistrictAI
from game.cars.zone.DistributedZoneAI import DistributedZoneAI
from game.cars.carplayer.InteractiveObjectAI import InteractiveObjectAI
from game.cars.racing.DistributedSinglePlayerRacingLobbyAI import DistributedSinglePlayerRacingLobbyAI

from typing import Dict

from game.cars.distributed.MongoInterface import MongoInterface

class CarsAIRepository(AIDistrict):
    notify = DirectNotifyGlobal.directNotify.newCategory("CarsAIRepository")

    def __init__(self, *args, **kw):
        AIDistrict.__init__(self, *args, **kw)

        self.playerTable: Dict[int, 'DistributedCarPlayerAI'] = {}

        self.mongoInterface = MongoInterface(self)

    def getGameDoId(self):
        return OTP_DO_ID_CARS

    def createObjects(self):
        # Create a new district (aka shard) for this AI:
        self.district = CarsDistrictAI(self, self.districtName)
        self.district.generateOtpObject(
                OTP_DO_ID_CARS, OTP_ZONE_ID_DISTRICTS,
                doId=self.districtId)

        # Generate zones:
        self.downtownZone = DistributedZoneAI(self, "Downtown Radiator Springs", ZoneConstants.DOWNTOWN_RADIATOR_SPRINGS)
        self.generateWithRequired(self.downtownZone, self.districtId, DUNGEON_INTEREST_HANDLE)

        self.fillmoresFields = DistributedZoneAI(self, "Fillmore's Fields", ZoneConstants.FILLMORES_FIELDS)
        self.generateWithRequired(self.fillmoresFields, self.districtId, DUNGEON_INTEREST_HANDLE)

        self.redhoodValley = DistributedZoneAI(self, "Redhood Valley", ZoneConstants.REDHOOD_VALLEY)
        self.generateWithRequired(self.redhoodValley, self.districtId, DUNGEON_INTEREST_HANDLE)

        self.willysButte = DistributedZoneAI(self, "Willy's Butte", ZoneConstants.WILLYS_BUTTE)
        self.generateWithRequired(self.willysButte, self.districtId, DUNGEON_INTEREST_HANDLE)

        self.mater = InteractiveObjectAI(self)
        self.mater.assetId = 31009 # materCatalogItemId
        self.generateWithRequired(self.mater, self.districtId, self.downtownZone.doId)

        self.downtownZone.interactiveObjects.append(self.mater)
        self.downtownZone.updateObjectCount()

        self.spRaceLobby = DistributedSinglePlayerRacingLobbyAI(self)
        self.generateWithRequired(self.spRaceLobby, self.district.doId, self.downtownZone.doId)

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
