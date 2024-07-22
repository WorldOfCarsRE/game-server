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
from game.cars.ai.HolidayManagerAI import HolidayManagerAI

from game.cars.ai.ServerBase import ServerBase
from game.cars.ai.ServerGlobals import WORLD_OF_CARS_ONLINE

from game.cars.distributed.MongoInterface import MongoInterface

import requests

class CarsAIRepository(AIDistrict, ServerBase):
    notify = DirectNotifyGlobal.directNotify.newCategory("CarsAIRepository")

    def __init__(self, *args, **kw):
        AIDistrict.__init__(self, *args, **kw)
        ServerBase.__init__(self)

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
        self.downtownZone.generateWithRequired(DUNGEON_INTEREST_HANDLE)

        self.fillmoresFields = DistributedZoneAI(self, "Fillmore's Fields", ZoneConstants.FILLMORES_FIELDS)
        self.fillmoresFields.generateWithRequired(DUNGEON_INTEREST_HANDLE)

        self.redhoodValley = DistributedZoneAI(self, "Redhood Valley", ZoneConstants.REDHOOD_VALLEY)
        self.redhoodValley.generateWithRequired(DUNGEON_INTEREST_HANDLE)

        self.willysButte = DistributedZoneAI(self, "Willy's Butte", ZoneConstants.WILLYS_BUTTE)
        self.willysButte.generateWithRequired(DUNGEON_INTEREST_HANDLE)

        self.mater = InteractiveObjectAI(self)
        self.mater.assetId = 31009 # materCatalogItemId
        self.mater.generateWithRequired(self.downtownZone.doId)

        self.downtownZone.interactiveObjects.append(self.mater)
        self.downtownZone.updateObjectCount()

        self.spRaceLobby = DistributedSinglePlayerRacingLobbyAI(self, "spRace_rh", 42002, "car_w_trk_tfn_twistinTailfin_SS_V1_phys.xml") # dungeonItemId is from constants.js
        self.spRaceLobby.generateWithRequired(self.redhoodValley.doId)

        self.holidayManager = HolidayManagerAI(self)
        # self.holidayManager.generateWithRequired(DUNGEON_INTEREST_HANDLE)

        # mark district as enabled
        # NOTE: Only setEnabled is used in the client
        # instead of setAvailable.
        self.district.b_setEnabled(1)

        if self.isProdServer():
            # Register us with the API server
            self.sendPopulation()

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
        if self.isProdServer():
            # This is the production server.
            # Send our population increase.
            self.sendPopulation()

        dg = PyDatagram()
        dg.addServerHeader(OTP_DO_ID_CARS_SHARD_MANAGER, self.ourChannel, SHARDMANAGER_UPDATE_SHARD)
        dg.addUint16(self.getPopulation())
        dg.addUint8(self.district.getEnabled())
        self.send(dg)

    def sendFriendManagerAccountOnline(self, accountId):
        dg = PyDatagram()
        dg.addServerHeader(OTP_DO_ID_PLAYER_FRIENDS_MANAGER, self.ourChannel, FRIENDMANAGER_ACCOUNT_ONLINE)
        dg.addUint32(accountId)
        self.send(dg)

    def sendFriendManagerAccountOffline(self, accountId):
        dg = PyDatagram()
        dg.addServerHeader(OTP_DO_ID_PLAYER_FRIENDS_MANAGER, self.ourChannel, FRIENDMANAGER_ACCOUNT_OFFLINE)
        dg.addUint32(accountId)
        self.send(dg)

    def sendPopulation(self):
        data = {
            'token': config.GetString('api-token'),
            'population': self.getPopulation(),
            'serverType': WORLD_OF_CARS_ONLINE,
            'shardName': self.districtName,
            'shardId': self.districtId
        }

        headers = {
            'User-Agent': 'Sunrise Games - CarsAIRepository'
        }

        try:
            requests.post('https://api.sunrise.games/api/setPopulation', json=data, headers=headers)
        except:
            self.notify.warning('Failed to send district population!')

    def incrementPopulation(self):
        AIDistrict.incrementPopulation(self)
        self.updateShard()

    def decrementPopulation(self):
        AIDistrict.decrementPopulation(self)
        self.updateShard()
