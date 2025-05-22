from typing import Dict, List

import requests
from direct.directnotify import DirectNotifyGlobal
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from game.cars.ai.CarsAIMsgTypes import *
from game.cars.ai.DatabaseObject import DatabaseObject
from game.cars.carplayer.DistributedCarPlayerAI import DistributedCarPlayerAI
from game.cars.carplayer.DistributedRaceCarAI import DistributedRaceCarAI
from game.cars.carplayer.games.DocsClinicAI import DocsClinicAI
from game.cars.carplayer.games.LuigisCasaDellaTiresAI import \
    LuigisCasaDellaTiresAI
from game.cars.carplayer.games.MatersSlingShootAI import MatersSlingShootAI
from game.cars.carplayer.npcs.MaterAI import MaterAI
from game.cars.carplayer.npcs.RamoneAI import RamoneAI
from game.cars.carplayer.npcs.TractorAI import TractorAI
from game.cars.carplayer.npcs.LightningMcQueenAI import LightningMcQueenAI
from game.cars.carplayer.shops.FillmoreFizzyFuelHutAI import \
    FillmoreFizzyFuelHutAI
from game.cars.carplayer.shops.MackShopAI import MackShopAI
from game.cars.carplayer.shops.SpyShopAI import SpyShopAI
from game.cars.carplayer.zones.GenericInteractiveObjectAI import GenericInteractiveObjectAI
from game.cars.carplayer.zones.HayBaleBombAI import HayBaleBombAI
from game.cars.carplayer.zones.MessyMixAI import MessyMixAI
from game.cars.carplayer.zones.RedhoodValleyAI import RedhoodValleyAI
from game.cars.carplayer.zones.SponsorBoothAI import SponsorBoothAI
from game.cars.carplayer.zones.WaterTowerAI import WaterTowerAI
from game.cars.distributed.CarsDistrictAI import CarsDistrictAI
from game.cars.distributed.CarsGlobals import *
from game.cars.distributed.MongoInterface import MongoInterface
from game.cars.dungeon.DistributedTutorialDungeonAI import DistributedTutorialDungeonAI
from game.cars.dungeon.DistributedYardAI import DistributedYardAI
from game.cars.racing.DistributedSinglePlayerRacingLobbyAI import \
    DistributedSinglePlayerRacingLobbyAI
from game.cars.racing.DistributedFriendsLobbyAI import \
    DistributedFriendsLobbyAI
from game.cars.racing.DistributedCrossShardLobbyAI import \
    DistributedCrossShardLobbyAI
from game.cars.zone import ZoneConstants
from game.cars.zone.DistributedZoneAI import DistributedZoneAI
from game.otp.ai.AIDistrict import AIDistrict
from game.otp.server.ServerBase import ServerBase
from game.otp.server.ServerGlobals import WORLD_OF_CARS_ONLINE


class CarsAIRepository(AIDistrict, ServerBase):
    notify = DirectNotifyGlobal.directNotify.newCategory("CarsAIRepository")

    def __init__(self, *args, **kw):
        AIDistrict.__init__(self, *args, **kw)
        ServerBase.__init__(self)

        self.mongoInterface = MongoInterface(self)

        self.staffMembers: List[int] = []
        self.accountMap: Dict[int, str] = {}

        self.shops = requests.get("http://127.0.0.1:8013/getShopItemData").json()
        self.notify.info(f"Loaded {len(self.shops)} shops item data.")

    def getShopItem(self, shopId: str, itemId: int) -> None | dict:
        for item in self.shops[shopId]:
            if item.get("itemId", 0) == itemId:
                return item

        return None

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

    def handlePlayGame(self, msgType, di):
        if msgType == SHARDMANAGER_ONLINE:
            # Re-transmit our shard information
            self.registerShard()
            self.updateShard()
        elif msgType == CARS_GENERATE_DUNGEON:
            self.handleGenerateDungeon(di)
        else:
            AIDistrict.handlePlayGame(self, msgType, di)

    def createObjects(self):
        # Create a new district (aka shard) for this AI:
        self.shardManagerClass = self.dclassesByName["ShardManager"]

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

        self.gasprin = SponsorBoothAI(self)
        self.gasprin.catalogId = 9989
        self.gasprin.name = "gasprin_main"
        self.gasprin.generateWithRequired(self.backfireCanyonSpeedway.doId)

        self.tankCoat = SponsorBoothAI(self)
        self.tankCoat.catalogId = 9990
        self.tankCoat.name = "tankcoat_main"
        self.tankCoat.generateWithRequired(self.backfireCanyonSpeedway.doId)

        self.backfireCanyonSpeedway.interactiveObjects.append(self.gasprin)
        self.backfireCanyonSpeedway.interactiveObjects.append(self.tankCoat)

        self.backfireCanyonSpeedway.updateObjectCount()

        self.noStall = SponsorBoothAI(self)
        self.noStall.catalogId = 9987
        self.noStall.name = "nostall_main"
        self.noStall.generateWithRequired(self.bigHeartlandSpeedway.doId)

        self.revNGo = SponsorBoothAI(self)
        self.revNGo.catalogId = 9988
        self.revNGo.name = "revngo_main"
        self.revNGo.generateWithRequired(self.bigHeartlandSpeedway.doId)

        self.bigHeartlandSpeedway.interactiveObjects.append(self.noStall)
        self.bigHeartlandSpeedway.interactiveObjects.append(self.revNGo)

        self.bigHeartlandSpeedway.updateObjectCount()

        self.mater = MaterAI(self)
        self.mater.generateWithRequired(self.downtownZone.doId)

        self.ramone = RamoneAI(self)
        self.ramone.generateWithRequired(self.downtownZone.doId)

        self.docsClinic = DocsClinicAI(self)
        self.docsClinic.generateWithRequired(self.downtownZone.doId)

        self.luigisCasaDellaTires = LuigisCasaDellaTiresAI(self)
        self.luigisCasaDellaTires.generateWithRequired(self.downtownZone.doId)

        self.redhoodValleyHotspot = RedhoodValleyAI(self)
        self.redhoodValleyHotspot.generateWithRequired(self.downtownZone.doId)

        self.spyShopRS = SpyShopAI(self)
        self.spyShopRS.name = "isostore_SpyStoreRS"
        self.spyShopRS.generateWithRequired(self.downtownZone.doId)

        for i in range(0, 22):
            cone = GenericInteractiveObjectAI(self)
            cone.name = f"cone{i}"
            cone.generateWithRequired(self.downtownZone.doId)
            self.downtownZone.interactiveObjects.append(cone)

        self.stanleyStatue = GenericInteractiveObjectAI(self)
        self.stanleyStatue.name = "rs_stanley_statue"
        self.stanleyStatue.generateWithRequired(self.downtownZone.doId)

        self.tireTower = GenericInteractiveObjectAI(self)
        self.tireTower.name = "rs_tire_tower"
        self.tireTower.generateWithRequired(self.downtownZone.doId)

        self.downtownZone.interactiveObjects.append(self.mater)
        self.downtownZone.interactiveObjects.append(self.ramone)
        self.downtownZone.interactiveObjects.append(self.docsClinic)
        self.downtownZone.interactiveObjects.append(self.luigisCasaDellaTires)
        self.downtownZone.interactiveObjects.append(self.stanleyStatue)
        self.downtownZone.interactiveObjects.append(self.tireTower)

        self.lightningMcQueen = LightningMcQueenAI(self)
        self.lightningMcQueen.generateWithRequired(self.downtownZone.doId)

        self.downtownZone.interactiveObjects.append(self.lightningMcQueen)

        self.downtownZone.interactiveObjects.append(self.redhoodValleyHotspot)
        self.downtownZone.interactiveObjects.append(self.spyShopRS)

        self.downtownZone.updateObjectCount()

        self.fillmoreFizzyHutFF = FillmoreFizzyFuelHutAI(self)
        self.fillmoreFizzyHutFF.name = "isostore_FillmoreFizzyHutFF"
        self.fillmoreFizzyHutFF.generateWithRequired(self.fillmoresFields.doId)

        self.spyShopFF = SpyShopAI(self)
        self.spyShopFF.name = "isostore_SpyStoreFF"
        self.spyShopFF.generateWithRequired(self.fillmoresFields.doId)

        self.tractor = TractorAI(self)
        self.tractor.name = 'tractor1'
        self.tractor.generateWithRequired(self.fillmoresFields.doId)

        for i in range(1, 14):
            hayBaleBomb = HayBaleBombAI(self)
            hayBaleBomb.name = f"hayBaleBomb_{i}"
            hayBaleBomb.generateWithRequired(self.fillmoresFields.doId)
            self.fillmoresFields.interactiveObjects.append(hayBaleBomb)

        for i in range(1, 4):
            waterTower = WaterTowerAI(self)
            waterTower.name = f"tower{i}"
            waterTower.generateWithRequired(self.fillmoresFields.doId)
            self.fillmoresFields.interactiveObjects.append(waterTower)

        for i in range(1, 10):
            messyMix = MessyMixAI(self)
            messyMix.name = f"ff_messy_mix_A_{i}"
            messyMix.generateWithRequired(self.fillmoresFields.doId)
            self.fillmoresFields.interactiveObjects.append(messyMix)

        self.fillmoresFields.interactiveObjects.append(self.fillmoreFizzyHutFF)
        self.fillmoresFields.interactiveObjects.append(self.spyShopFF)
        self.fillmoresFields.interactiveObjects.append(self.tractor)

        self.fillmoresFields.updateObjectCount()

        self.rusteze = SponsorBoothAI(self)
        self.rusteze.catalogId = 9995
        self.rusteze.name = "rusteze_main"
        self.rusteze.generateWithRequired(self.laSpeedway.doId)

        self.nitroAde = SponsorBoothAI(self)
        self.nitroAde.catalogId = 9996
        self.nitroAde.name = "nitroade_main"
        self.nitroAde.generateWithRequired(self.laSpeedway.doId)

        self.octaneGain = SponsorBoothAI(self)
        self.octaneGain.catalogId = 9997
        self.octaneGain.name = "octane_main"
        self.octaneGain.generateWithRequired(self.laSpeedway.doId)

        self.n2oCola = SponsorBoothAI(self)
        self.n2oCola.catalogId = 9998
        self.n2oCola.name = "n2o_main"
        self.n2oCola.generateWithRequired(self.laSpeedway.doId)

        self.dinoco = SponsorBoothAI(self)
        self.dinoco.catalogId = 9999
        self.dinoco.name = "dinoco_main"
        self.dinoco.generateWithRequired(self.laSpeedway.doId)

        self.moodSprings = SponsorBoothAI(self)
        self.moodSprings.catalogId = 10000
        self.moodSprings.name = "moodsprings_main"
        self.moodSprings.generateWithRequired(self.laSpeedway.doId)

        self.laSpeedway.interactiveObjects.append(self.rusteze)
        self.laSpeedway.interactiveObjects.append(self.nitroAde)
        self.laSpeedway.interactiveObjects.append(self.octaneGain)
        self.laSpeedway.interactiveObjects.append(self.n2oCola)
        self.laSpeedway.interactiveObjects.append(self.dinoco)
        self.laSpeedway.interactiveObjects.append(self.moodSprings)

        self.laSpeedway.updateObjectCount()

        self.vitoline = SponsorBoothAI(self)
        self.vitoline.catalogId = 9993
        self.vitoline.name = "vitoline_main"
        self.vitoline.generateWithRequired(self.motorSpeedwaySouth.doId)

        self.viewZeen = SponsorBoothAI(self)
        self.viewZeen.catalogId = 9994
        self.viewZeen.name = "vuzeen_main"
        self.viewZeen.generateWithRequired(self.motorSpeedwaySouth.doId)

        self.motorSpeedwaySouth.interactiveObjects.append(self.vitoline)
        self.motorSpeedwaySouth.interactiveObjects.append(self.viewZeen)

        self.motorSpeedwaySouth.updateObjectCount()

        self.reVolting = SponsorBoothAI(self)
        self.reVolting.catalogId = 9991
        self.reVolting.name = "revolting_main"
        self.reVolting.generateWithRequired(self.petroleumCitySpeedway.doId)

        self.htB = SponsorBoothAI(self)
        self.htB.catalogId = 9992
        self.htB.name = "htb_main"
        self.htB.generateWithRequired(self.petroleumCitySpeedway.doId)

        self.petroleumCitySpeedway.interactiveObjects.append(self.reVolting)
        self.petroleumCitySpeedway.interactiveObjects.append(self.htB)

        self.petroleumCitySpeedway.updateObjectCount()

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

        self.shinyWax = SponsorBoothAI(self)
        self.shinyWax.catalogId = 9980
        self.shinyWax.name = "shinywax_generic"
        self.shinyWax.generateWithRequired(self.tailgatorSpeedway.doId)

        self.leakLess = SponsorBoothAI(self)
        self.leakLess.catalogId = 9981
        self.leakLess.name = "leakless_generic"
        self.leakLess.generateWithRequired(self.tailgatorSpeedway.doId)

        self.sputterStop = SponsorBoothAI(self)
        self.sputterStop.catalogId = 9982
        self.sputterStop.name = "sputter_generic"
        self.sputterStop.generateWithRequired(self.tailgatorSpeedway.doId)

        self.spareMint = SponsorBoothAI(self)
        self.spareMint.catalogId = 9983
        self.spareMint.name = "sparemint_generic"
        self.spareMint.generateWithRequired(self.tailgatorSpeedway.doId)

        self.trunkFresh = SponsorBoothAI(self)
        self.trunkFresh.catalogId = 9984
        self.trunkFresh.name = "trunkfresh_generic"
        self.trunkFresh.generateWithRequired(self.tailgatorSpeedway.doId)

        self.lilTorquey = SponsorBoothAI(self)
        self.lilTorquey.catalogId = 9985
        self.lilTorquey.name = "torquey_main"
        self.lilTorquey.generateWithRequired(self.tailgatorSpeedway.doId)

        self.gaskits = SponsorBoothAI(self)
        self.gaskits.catalogId = 9986
        self.gaskits.name = "gaskit_main"
        self.gaskits.generateWithRequired(self.tailgatorSpeedway.doId)

        self.tailgatorSpeedway.interactiveObjects.append(self.shinyWax)
        self.tailgatorSpeedway.interactiveObjects.append(self.leakLess)
        self.tailgatorSpeedway.interactiveObjects.append(self.sputterStop)
        self.tailgatorSpeedway.interactiveObjects.append(self.spareMint)
        self.tailgatorSpeedway.interactiveObjects.append(self.trunkFresh)
        self.tailgatorSpeedway.interactiveObjects.append(self.lilTorquey)
        self.tailgatorSpeedway.interactiveObjects.append(self.gaskits)

        self.tailgatorSpeedway.updateObjectCount()

        self.fillmoreFizzyHutWB = FillmoreFizzyFuelHutAI(self)
        self.fillmoreFizzyHutWB.name = "isostore_fillmoreFizzyHutWB"
        self.fillmoreFizzyHutWB.generateWithRequired(self.willysButte.doId)

        self.matersSlingShoot = MatersSlingShootAI(self)
        self.matersSlingShoot.generateWithRequired(self.willysButte.doId)

        self.spyShopWB = SpyShopAI(self)
        self.spyShopWB.name = "isostore_SpyStoreWB"
        self.spyShopWB.generateWithRequired(self.willysButte.doId)

        self.willysButte.interactiveObjects.append(self.fillmoreFizzyHutWB)
        self.willysButte.interactiveObjects.append(self.matersSlingShoot)
        self.willysButte.interactiveObjects.append(self.spyShopWB)

        self.willysButte.updateObjectCount()

        self.spCCSRaceLobby = DistributedSinglePlayerRacingLobbyAI(self, "spRace_ccs", 42001, "car_w_trk_rsp_ccSpeedway_SS_phys.xml") # dungeonItemId is from constants.js
        self.spCCSRaceLobby.generateWithRequired(self.downtownZone.doId)

        self.mpCCSRaceFriendsLobby = DistributedFriendsLobbyAI(self, "mpRace_ccs", 42001, "car_w_trk_rsp_ccSpeedway_SS_phys.xml")
        self.mpCCSRaceFriendsLobby.generateWithRequired(self.downtownZone.doId)

        self.mpCCSRaceCrossShardLobby = DistributedCrossShardLobbyAI(self, "mpRace_ccs", 42001, "car_w_trk_rsp_ccSpeedway_SS_phys.xml")
        self.mpCCSRaceCrossShardLobby.generateWithRequired(self.downtownZone.doId)

        self.spRHRaceLobby = DistributedSinglePlayerRacingLobbyAI(self, "spRace_rh", 42002, "car_w_trk_tfn_twistinTailfin_SS_V1_phys.xml") # dungeonItemId is from constants.js
        self.spRHRaceLobby.generateWithRequired(self.redhoodValley.doId)

        self.mpRHRaceFriendsLobby = DistributedFriendsLobbyAI(self, "mpRace_rh", 42002, "car_w_trk_tfn_twistinTailfin_SS_V1_phys.xml")
        self.mpRHRaceFriendsLobby.generateWithRequired(self.redhoodValley.doId)

        self.mpRHRaceCrossShardLobby = DistributedCrossShardLobbyAI(self, "mpRace_rh", 42002, "car_w_trk_tfn_twistinTailfin_SS_V1_phys.xml")
        self.mpRHRaceCrossShardLobby.generateWithRequired(self.redhoodValley.doId)

        self.spWBRaceLobby = DistributedSinglePlayerRacingLobbyAI(self, "spRace_wb", 42005, "car_w_trk_wil_WillysButte_SS_phys.xml") # dungeonItemId is from constants.js
        self.spWBRaceLobby.generateWithRequired(self.willysButte.doId)

        self.mpWBRaceFriendsLobby = DistributedFriendsLobbyAI(self, "mpRace_wb", 42005, "car_w_trk_wil_WillysButte_SS_phys.xml")
        self.mpWBRaceFriendsLobby.generateWithRequired(self.willysButte.doId)

        self.mpWBRaceCrossShardLobby = DistributedCrossShardLobbyAI(self, "mpRace_wb", 42005, "car_w_trk_wil_WillysButte_SS_phys.xml")
        self.mpWBRaceCrossShardLobby.generateWithRequired(self.willysButte.doId)

        self.spFFRRaceLobby = DistributedSinglePlayerRacingLobbyAI(self, "spRace_ffr", 42003, "car_w_trk_frm_ffRally_SS_phys.xml") # dungeonItemId is from constants.js
        self.spFFRRaceLobby.generateWithRequired(self.fillmoresFields.doId)

        self.mpFFRRaceFriendsLobby = DistributedFriendsLobbyAI(self, "mpRace_ffr", 42003, "car_w_trk_frm_ffRally_SS_phys.xml")
        self.mpFFRRaceFriendsLobby.generateWithRequired(self.fillmoresFields.doId)

        self.mpFFRRaceCrossShardLobby = DistributedCrossShardLobbyAI(self, "mpRace_ffr", 42003, "car_w_trk_frm_ffRally_SS_phys.xml")
        self.mpFFRRaceCrossShardLobby.generateWithRequired(self.fillmoresFields.doId)

        self.tgsRaceFriendsLobby = DistributedFriendsLobbyAI(self, "race_tgs", 42004, "car_w_trk_prf_tailgator_SS_phys.xml")
        self.tgsRaceFriendsLobby.generateWithRequired(self.tailgatorSpeedway.doId)

        self.tgsRaceLobby = DistributedCrossShardLobbyAI(self, "race_tgs", 42004, "car_w_trk_prf_tailgator_SS_phys.xml")
        self.tgsRaceLobby.generateWithRequired(self.tailgatorSpeedway.doId)

        self.bhsRaceFriendsLobby = DistributedFriendsLobbyAI(self, "race_bhl", 42006, "car_w_trk_prf_BigHeartland_SS_phys.xml")
        self.bhsRaceFriendsLobby.generateWithRequired(self.bigHeartlandSpeedway.doId)

        self.bhsRaceLobby = DistributedCrossShardLobbyAI(self, "race_bhl", 42006, "car_w_trk_prf_BigHeartland_SS_phys.xml")
        self.bhsRaceLobby.generateWithRequired(self.bigHeartlandSpeedway.doId)

        self.bfcRaceFriendsLobby = DistributedFriendsLobbyAI(self, "race_bfc", 42007, "car_w_trk_prf_BackfireCanyon_SS_phys.xml")
        self.bfcRaceFriendsLobby.generateWithRequired(self.backfireCanyonSpeedway.doId)

        self.bfcRaceLobby = DistributedCrossShardLobbyAI(self, "race_bfc", 42007, "car_w_trk_prf_BackfireCanyon_SS_phys.xml")
        self.bfcRaceLobby.generateWithRequired(self.backfireCanyonSpeedway.doId)

        self.pcRaceFriendsLobby = DistributedFriendsLobbyAI(self, "race_pc", 42008, "car_w_trk_prf_PetroleumCityRace_SS_phys.xml")
        self.pcRaceFriendsLobby.generateWithRequired(self.petroleumCitySpeedway.doId)

        self.pcRaceLobby = DistributedCrossShardLobbyAI(self, "race_pc", 42008, "car_w_trk_prf_PetroleumCityRace_SS_phys.xml")
        self.pcRaceLobby.generateWithRequired(self.petroleumCitySpeedway.doId)

        self.mssRaceFriendsLobby = DistributedFriendsLobbyAI(self, "race_mss", 42009, "car_w_trk_prf_MotorSpeedwaySouth_SS_phys.xml")
        self.mssRaceFriendsLobby.generateWithRequired(self.motorSpeedwaySouth.doId)

        self.mssRaceLobby = DistributedCrossShardLobbyAI(self, "race_mss", 42009, "car_w_trk_prf_MotorSpeedwaySouth_SS_phys.xml")
        self.mssRaceLobby.generateWithRequired(self.motorSpeedwaySouth.doId)

        self.lasRaceFriendsLobby = DistributedFriendsLobbyAI(self, "race_las", 42010, "car_w_trk_prf_LASpeedway_SS_phys.xml")
        self.lasRaceFriendsLobby.generateWithRequired(self.laSpeedway.doId)

        self.lasRaceLobby = DistributedCrossShardLobbyAI(self, "race_las", 42010, "car_w_trk_prf_LASpeedway_SS_phys.xml")
        self.lasRaceLobby.generateWithRequired(self.laSpeedway.doId)

        # mark district as enabled
        # NOTE: Only setEnabled is used in the client
        # instead of setAvailable.
        self.district.b_setEnabled(1)

        if self.isProdServer():
            # Register us with the API server
            self.sendPopulation()

        self.notify.info("Ready!")

    def registerShard(self):
        # Send update to the ShardManager UberDOG
        dg = self.shardManagerClass.aiFormatUpdate("registerShard", OTP_DO_ID_CARS_SHARD_MANAGER, OTP_DO_ID_CARS_SHARD_MANAGER, self.ourChannel, (self.districtId, self.districtName))
        self.send(dg)

        # Set up the delete message as a post remove
        dg = self.shardManagerClass.aiFormatUpdate("deleteShard", OTP_DO_ID_CARS_SHARD_MANAGER, OTP_DO_ID_CARS_SHARD_MANAGER, self.ourChannel, [])
        self.addPostSocketClose(dg)

    def updateShard(self):
        if self.isProdServer():
            # This is the production server.
            # Send our population update.
            self.sendPopulation()

        dg = self.shardManagerClass.aiFormatUpdate("updateShard", OTP_DO_ID_CARS_SHARD_MANAGER, OTP_DO_ID_CARS_SHARD_MANAGER, self.ourChannel, (self.getPopulation(), self.district.getEnabled()))
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
        dbo.readObject(carPlayer, ["setCarCoins", "setYardStocks"])

    def readRaceCar(self, racecarId, fields = None, doneEvent = '') -> DistributedRaceCarAI:
        dbo = DatabaseObject(self, racecarId, doneEvent)
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

    def handleGenerateDungeon(self, di):
        sender = self.getMsgSender()
        context = di.getUint32()
        _type = di.getUint8()
        lobbyDoId = di.getUint32()
        contextDoId = di.getUint32()
        playerIds = []
        while di.getRemainingSize() > 0:
            playerIds.append(di.getUint32())

        dungeon = None
        if _type == DUNGEON_TYPE_TUTORIAL:
            dungeon = DistributedTutorialDungeonAI(self)

            dungeon.playerIds = playerIds
            dungeon.lobbyDoId = lobbyDoId
            dungeon.contextDoId = contextDoId

            zoneId = self.allocateZone()
            dungeon.generateWithRequired(zoneId)
            dungeon.createObjects()
        elif _type == DUNGEON_TYPE_YARD:
            dungeon = DistributedYardAI(self, playerIds[0])
            dungeon.generateOtpObject(self.districtId, dungeon.owner)
            dungeon.createObjects()
        elif _type == DUNGEON_TYPE_RACE:
            self.notify.warning("TODO: DUNGEON_TYPE_RACE")
            return
        else:
            self.notify.warning(f"Ignoring unknown dungeon type {_type} from CARS_GENERATE_DUNGEON")
            return

        dg = PyDatagram()
        dg.addServerHeader(sender, self.ourChannel, CARS_GENERATE_DUNGEON_RESP)
        dg.addUint32(context)
        dg.addUint32(dungeon.doId)
        dg.addUint32(dungeon.parentId)
        dg.addUint32(dungeon.zoneId)
        self.send(dg)
