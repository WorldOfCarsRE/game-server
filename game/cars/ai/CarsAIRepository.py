from typing import Dict, List

import requests
from direct.directnotify import DirectNotifyGlobal
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator

from game.cars.ai.CarsAIMsgTypes import *
from game.cars.ai.DatabaseObject import DatabaseObject
from game.cars.ai.HolidayManagerAI import HolidayManagerAI
from game.cars.ai.ServerBase import ServerBase
from game.cars.ai.ServerGlobals import WORLD_OF_CARS_ONLINE
from game.cars.carplayer.DistributedCarPlayerAI import DistributedCarPlayerAI
from game.cars.carplayer.DistributedRaceCarAI import DistributedRaceCarAI
from game.cars.carplayer.games.DocsClinicAI import DocsClinicAI
from game.cars.carplayer.games.LuigisCasaDellaTiresAI import \
    LuigisCasaDellaTiresAI
from game.cars.carplayer.games.MatersSlingShootAI import MatersSlingShootAI
from game.cars.carplayer.npcs.MaterAI import MaterAI
from game.cars.carplayer.npcs.RamoneAI import RamoneAI
from game.cars.carplayer.npcs.TractorAI import TractorAI
from game.cars.carplayer.shops.FillmoreFizzyFuelHutAI import FillmoreFizzyFuelHutAI
from game.cars.carplayer.shops.MackShopAI import MackShopAI
from game.cars.carplayer.shops.SpyShopAI import SpyShopAI
from game.cars.carplayer.zones.ConeAI import ConeAI
from game.cars.carplayer.zones.RedhoodValleyAI import RedhoodValleyAI
from game.cars.distributed.CarsDistrictAI import CarsDistrictAI
from game.cars.distributed.CarsGlobals import *
from game.cars.distributed.MongoInterface import MongoInterface
from game.cars.racing.DistributedSinglePlayerRacingLobbyAI import \
    DistributedSinglePlayerRacingLobbyAI
from game.cars.zone import ZoneConstants
from game.cars.zone.DistributedZoneAI import DistributedZoneAI
from game.otp.ai.AIDistrict import AIDistrict


class CarsAIRepository(AIDistrict, ServerBase):
    notify = DirectNotifyGlobal.directNotify.newCategory("CarsAIRepository")

    def __init__(self, *args, **kw):
        AIDistrict.__init__(self, *args, **kw)
        ServerBase.__init__(self)

        self.mongoInterface = MongoInterface(self)

        self.staffMembers: List[int] = []
        self.accountMap: Dict[int, str] = {}

    def getGameDoId(self):
        return OTP_DO_ID_CARS

    def getMinDynamicZone(self):
        # Override this to return the minimum allowable value for a
        # dynamically-allocated zone id.
        return DynamicZonesBegin

    def getMaxDynamicZone(self):
        # Override this to return the maximum allowable value for a
        # dynamically-allocated zone id.

        # Note that each zone requires the use of the channel derived
        # by self.districtId + zoneId.  Thus, we cannot have any zones
        # greater than or equal to self.minChannel - self.districtId,
        # which is our first allocated doId.
        return min(self.minChannel - self.districtId, DynamicZonesEnd) - 1

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

        self.tailgatorSpeedway = DistributedZoneAI(self, "Tailgator Speedway", ZoneConstants.TAILGATOR_SPEEDWAY)
        self.tailgatorSpeedway.generateWithRequired(DUNGEON_INTEREST_HANDLE)

        self.bigHeartlandSpeedway = DistributedZoneAI(self, "Big Heartland Speedway", ZoneConstants.BIG_HEARTLAND_SPEEDWAY)
        self.bigHeartlandSpeedway.generateWithRequired(DUNGEON_INTEREST_HANDLE)

        self.backfireCanyonSpeedway = DistributedZoneAI(self, "Backfire Canyon Speedway", ZoneConstants.BACKFIRE_CANYON_SPEEDWAY)
        self.backfireCanyonSpeedway.generateWithRequired(DUNGEON_INTEREST_HANDLE)

        self.petroleumCitySpeedway = DistributedZoneAI(self, "Petroleum City Super Speedway", ZoneConstants.PETROLEUM_CITY_SPEEDWAY)
        self.petroleumCitySpeedway.generateWithRequired(DUNGEON_INTEREST_HANDLE)

        self.motorSpeedwaySouth = DistributedZoneAI(self, "Motor Speedway of the South", ZoneConstants.MOTOR_SOUTH_SPEEDWAY)
        self.motorSpeedwaySouth.generateWithRequired(DUNGEON_INTEREST_HANDLE)

        self.laSpeedway = DistributedZoneAI(self, "LA International Speedway", ZoneConstants.LA_SPEEDWAY)
        self.laSpeedway.generateWithRequired(DUNGEON_INTEREST_HANDLE)

        self.mater = MaterAI(self)
        self.mater.generateWithRequired(self.downtownZone.doId)

        self.ramone = RamoneAI(self)
        self.ramone.generateWithRequired(self.downtownZone.doId)

        self.docsClinic = DocsClinicAI(self)
        self.docsClinic.generateWithRequired(self.downtownZone.doId)

        self.luigisCasaDellaTires = LuigisCasaDellaTiresAI(self)
        self.luigisCasaDellaTires.generateWithRequired(self.downtownZone.doId)

        self.matersSlingShoot = MatersSlingShootAI(self)
        self.matersSlingShoot.generateWithRequired(self.downtownZone.doId)

        self.redhoodValleyHotspot = RedhoodValleyAI(self)
        self.redhoodValleyHotspot.generateWithRequired(self.downtownZone.doId)

        self.spyShopRS = SpyShopAI(self)
        self.spyShopRS.name = "isostore_SpyStoreRS"
        self.spyShopRS.generateWithRequired(self.downtownZone.doId)

        for i in range(0, 22):
            cone = ConeAI(self)
            cone.name = f"cone{i}"
            cone.generateWithRequired(self.downtownZone.doId)
            self.downtownZone.interactiveObjects.append(cone)

        self.downtownZone.interactiveObjects.append(self.mater)
        self.downtownZone.interactiveObjects.append(self.ramone)
        self.downtownZone.interactiveObjects.append(self.docsClinic)
        self.downtownZone.interactiveObjects.append(self.luigisCasaDellaTires)
        self.downtownZone.interactiveObjects.append(self.matersSlingShoot)
        self.downtownZone.interactiveObjects.append(self.redhoodValleyHotspot)
        self.downtownZone.interactiveObjects.append(self.spyShopRS)

        self.downtownZone.updateObjectCount()

        self.fillmoreFizzyHutFF = FillmoreFizzyFuelHutAI(self)
        self.fillmoreFizzyHutFF.name = "isostore_FillmoreFizzyHutFF"
        self.fillmoreFizzyHutFF.generateWithRequired(self.fillmoresFields.doId)

        self.tractor = TractorAI(self)
        self.tractor.name = 'tractor1'
        self.tractor.generateWithRequired(self.fillmoresFields.doId)

        self.fillmoresFields.interactiveObjects.append(self.fillmoreFizzyHutFF)
        self.fillmoresFields.interactiveObjects.append(self.tractor)

        self.fillmoresFields.updateObjectCount()

        self.fillmoreFizzyHutRV = FillmoreFizzyFuelHutAI(self)
        self.fillmoreFizzyHutRV.generateWithRequired(self.redhoodValley.doId)

        self.mackShop = MackShopAI(self)
        self.mackShop.generateWithRequired(self.redhoodValley.doId)

        self.spyShopRV = SpyShopAI(self)
        self.spyShopRV.generateWithRequired(self.redhoodValley.doId)

        self.redhoodValley.interactiveObjects.append(self.fillmoreFizzyHutRV)
        self.redhoodValley.interactiveObjects.append(self.mackShop)
        self.redhoodValley.interactiveObjects.append(self.spyShopRV)

        self.redhoodValley.updateObjectCount()

        self.fillmoreFizzyHutWB = FillmoreFizzyFuelHutAI(self)
        self.fillmoreFizzyHutWB.name = "isostore_fillmoreFizzyHutWB"
        self.fillmoreFizzyHutWB.generateWithRequired(self.willysButte.doId)
        
        self.willysButte.interactiveObjects.append(self.fillmoreFizzyHutWB)

        self.willysButte.updateObjectCount()

        # self.spCCSRaceLobby = DistributedSinglePlayerRacingLobbyAI(self, "spRace_ccs", 42001, "car_w_trk_rsp_ccSpeedway_SS_phys.xml") # dungeonItemId is from constants.js
        # self.spCCSRaceLobby.generateWithRequired(self.downtownZone.doId)

        self.spRHRaceLobby = DistributedSinglePlayerRacingLobbyAI(self, "spRace_rh", 42002, "car_w_trk_tfn_twistinTailfin_SS_V1_phys.xml") # dungeonItemId is from constants.js
        self.spRHRaceLobby.generateWithRequired(self.redhoodValley.doId)

        self.spWBRaceLobby = DistributedSinglePlayerRacingLobbyAI(self, "spRace_wb", 42005, "car_w_trk_wil_WillysButte_SS_phys.xml") # dungeonItemId is from constants.js
        self.spWBRaceLobby.generateWithRequired(self.willysButte.doId)

        self.spFFRRaceLobby = DistributedSinglePlayerRacingLobbyAI(self, "spRace_ffr", 42003, "car_w_trk_frm_ffRally_SS_phys.xml") # dungeonItemId is from constants.js
        self.spFFRRaceLobby.generateWithRequired(self.fillmoresFields.doId)

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
            # Send our population update.
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

    def fillInCarsPlayer(self, carPlayer) -> None:
        dbo = DatabaseObject(self, carPlayer.doId)
        # Add more fields if needed. (Good spot to look if the field you want
        # is an ownrequired field, but no required or ram.)
        dbo.readObject(carPlayer, ["setCarCoins"])

    def readRaceCar(self, racecarId, fields = None) -> DistributedRaceCarAI:
        dbo = DatabaseObject(self, racecarId)
        return dbo.readRaceCar(fields)

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

    def setAllowModerationActions(self, accountId: int, accountType: str) -> None:
        if accountId not in self.staffMembers:
            self.staffMembers.append(accountId)
            self.accountMap[accountId] = accountType
