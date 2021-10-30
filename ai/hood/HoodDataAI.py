from ai.globals.HoodGlobals import *
from typing import List, Dict, Union, Optional
from ai.DistributedObjectAI import DistributedObjectAI
from dna.dnaparser import load_dna_file, DNAStorage
from dna.objects import DNAGroup, DNAVisGroup
from ai.toon import NPCToons
from ai.fishing.FishingAI import DistributedFishingPondAI, DistributedFishingSpotAI
from ai.safezone import ButterflyGlobals
from ai.safezone.DistributedButterflyAI import DistributedButterflyAI
from ai.trolley.DistributedTrolleyAI import DistributedTrolleyAI
from ai.suit.DistributedSuitPlannerAI import DistributedSuitPlannerAI
from .Treasures import *
from typing import Type

# TODO: maybe add dist obj stuff

DNA_MAP = {
    DonaldsDock: 'donalds_dock_sz.dna',
    BarnacleBoulevard: 'donalds_dock_1100.dna',
    SeaweedStreet: 'donalds_dock_1200.dna',
    LighthouseLane: 'donalds_dock_1300.dna',
    ToontownCentral: 'toontown_central_sz.dna',
    SillyStreet: 'toontown_central_2100.dna',
    LoopyLane: 'toontown_central_2200.dna',
    PunchlinePlace: 'toontown_central_2300.dna',
    TheBrrrgh: 'the_burrrgh_sz.dna',
    WalrusWay: 'the_burrrgh_3100.dna',
    SleetStreet: 'the_burrrgh_3200.dna',
    PolarPlace: 'the_burrrgh_3300.dna',
    MinniesMelodyland: 'minnies_melody_land_sz.dna',
    AltoAvenue: 'minnies_melody_land_4100.dna',
    BaritoneBoulevard: 'minnies_melody_land_4200.dna',
    TenorTerrace: 'minnies_melody_land_4300.dna',
    DaisyGardens: 'daisys_garden_sz.dna',
    ElmStreet: 'daisys_garden_5100.dna',
    MapleStreet: 'daisys_garden_5200.dna',
    OakStreet: 'daisys_garden_5300.dna',
    DonaldsDreamland: 'donalds_dreamland_sz.dna',
    LullabyLane: 'donalds_dreamland_9100.dna',
    PajamaPlace: 'donalds_dreamland_9200.dna',
    SellbotHQ: 'cog_hq_sellbot_sz.dna',
    SellbotFactoryExt: 'cog_hq_sellbot_11200.dna',
    CashbotHQ: 'cog_hq_cashbot_sz.dna',
    LawbotHQ: 'cog_hq_lawbot_sz.dna',
}

class PlaceAI:
    def __init__(self, air, zone_id):
        self.air = air
        self.zone_id: int = zone_id

        self._active = False
        # self.doTable: Dict[int, DistributedObjectAI] = {}
        self.storage: Tuple[DNAStorage] = {}
        self.dna: Tuple[DNAGroup] = {}

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, active: bool):
        if self._active == active:
            return

        self._active = active

        if active:
            self.create()
        else:
            self.cleanup()

    def create(self):
        raise NotImplementedError

    def cleanup(self):
        raise NotImplementedError

from ai.building.DistributedHQInteriorAI import DistributedHQInteriorAI
from ai.building.DistributedDoorAI import DistributedDoorAI, DistributedCogHQDoorAI
from ai.building import DoorTypes

class HQBuildingAI(object):
    __slots__ = 'interior', 'door0', 'door1', 'insideDoor0', 'insideDoor1', 'npcs'

    def __init__(self, air, exteriorZone, interiorZone, block):
        self.interior = DistributedHQInteriorAI(block, air, interiorZone)
        self.interior.generateWithRequired(interiorZone)

        door0 = DistributedDoorAI(air, block, DoorTypes.EXT_HQ, doorIndex=0)
        door0.zoneId = exteriorZone

        door1 = DistributedDoorAI(air, block, DoorTypes.EXT_HQ, doorIndex=1)
        door1.zoneId = exteriorZone

        insideDoor0 = DistributedDoorAI(air, block, DoorTypes.INT_HQ, doorIndex=0)
        insideDoor0.zoneId = interiorZone

        insideDoor1 = DistributedDoorAI(air, block, DoorTypes.INT_HQ, doorIndex=1)
        insideDoor1.zoneId = interiorZone

        door0.setOtherDoor(insideDoor0)
        door1.setOtherDoor(insideDoor1)
        insideDoor0.setOtherDoor(door0)
        insideDoor1.setOtherDoor(door1)

        door0.generateWithRequired(exteriorZone)
        door1.generateWithRequired(exteriorZone)
        insideDoor0.generateWithRequired(interiorZone)
        insideDoor1.generateWithRequired(interiorZone)

        self.door0 = door0
        self.door1 = door1
        self.insideDoor0 = insideDoor0
        self.insideDoor1 = insideDoor1

        # TODO
        self.npcs = NPCToons.createNpcsInZone(air, interiorZone)

    def delete(self):
        for npc in self.npcs:
            npc.requestDelete()
        self.door0.requestDelete()
        self.door1.requestDelete()
        self.insideDoor0.requestDelete()
        self.insideDoor1.requestDelete()
        self.interior.requestDelete()

class GagshopBuildingAI(object):
    __slots__ = 'interior', 'door', 'insideDoor', 'npcs'

    def __init__(self, air, exteriorZone, interiorZone, block):
        self.interior = DistributedGagshopInteriorAI(air, block, interiorZone)
        self.interior.generateWithRequired(interiorZone)

        door = DistributedDoorAI(air, block, DoorTypes.EXT_STANDARD)
        door.zoneId = exteriorZone

        insideDoor = DistributedDoorAI(air, block, DoorTypes.INT_STANDARD)
        insideDoor.zoneId = interiorZone

        door.setOtherDoor(insideDoor)
        insideDoor.setOtherDoor(door)

        door.generateWithRequired(exteriorZone)
        insideDoor.generateWithRequired(interiorZone)
        self.door = door
        self.insideDoor = insideDoor

        self.npcs = NPCToons.createNpcsInZone(air, interiorZone)

    def cleanup(self):
        for npc in self.npcs:
            npc.requestDelete()

        self.door.requestDelete()
        self.insideDoor.requestDelete()
        self.interior.requestDelete()

class DistributedGagshopInteriorAI(DistributedObjectAI):
    def __init__(self, air, block, zoneId):
        DistributedObjectAI.__init__(self, air)
        self.block = block
        self.zoneId = zoneId

    def getZoneIdAndBlock(self):
        return self.zoneId, self.block

from ai.building.DistributedBuildingAI import DistributedBuildingAI

class SafeZoneAI(PlaceAI):

    def __init__(self, air, zone_id):
        PlaceAI.__init__(self, air, zone_id)
        self.buildings: Dict[int, object] = {}
        self.hq: Union[HQBuildingAI, None] = None
        self.gagShop: Union[GagshopBuildingAI, None] = None

    @staticmethod
    def getInteriorZone(zoneId, block):
        return zoneId - zoneId % 100 + 500 + block

    def create(self):
        self.dna[self.zone_id], self.storage[self.zone_id] = load_dna_file('dna/files/' + DNA_MAP[self.zone_id])

        for block in self.storage[self.zone_id].blocks:
            buildingType = self.storage[self.zone_id].block_building_types[block]
            interiorZone = self.getInteriorZone(self.zone_id, block)
            exteriorZone = self.storage[self.zone_id].block_zones.get(block, self.zone_id)

            if buildingType == 'hq':
                self.buildings[block] = HQBuildingAI(self.air, exteriorZone, interiorZone, block)
            elif buildingType == 'gagshop':
                self.buildings[block] = GagshopBuildingAI(self.air, exteriorZone, interiorZone, block)
            elif buildingType == 'petshop':
                # TODO
                pass
            elif buildingType == 'kartshop':
                # TODO
                pass
            elif buildingType == 'animbldg':
                # TODO
                pass
            else:
                bldg = DistributedBuildingAI(self.air)
                bldg.block = block
                bldg.exteriorZoneId = exteriorZone
                bldg.interiorZoneId = self.getInteriorZone(exteriorZone, block)
                bldg.generateWithRequired(self.zone_id)
                bldg.request('Toon')
                self.buildings[block] = bldg

        for visgroup in self.storage[self.zone_id].visgroups:
            zone = int(visgroup.name.split(':')[0])
            visibles = visgroup.visibles
            if self.zone_id not in visibles:
                visibles.append(self.zone_id)
            self.air.vismap[zone] = tuple(visibles)

        pondName2Do = {}

        for pondName in self.storage[self.zone_id].ponds:
            group = self.storage[self.zone_id].groups[pondName]
            visName = group.get_vis_group().name
            if ':' in visName:
                zoneId = int(visName.split(':')[0])
            else:
                zoneId = int(visName)

            pond = DistributedFishingPondAI(self.air, self.zone_id)
            pond.generateWithRequired(zoneId)
            pondName2Do[pondName] = pond

        for dnaspot in self.storage[self.zone_id].spots:
            group = dnaspot.get_group()
            pondName = dnaspot.get_pond_name()
            pond = pondName2Do[pondName]
            spot = DistributedFishingSpotAI(self.air, pond, group.get_pos_hpr())
            spot.generateWithRequired(pond.zoneId)

        del pondName2Do

class StreetAI(SafeZoneAI):
    def __init__(self, air, zone_id):
        SafeZoneAI.__init__(self, air, zone_id)

        self.wantSuits = False
        self.suitPlanner: Optional[DistributedSuitPlannerAI] = None

    def create(self):
        super().create()

        # TODO: suits
        if self.wantSuits:
            self.suitPlanner = DistributedSuitPlannerAI(self.air, self, self.zone_id)
            self.suitPlanner.generateWithRequired(self.zone_id)
            self.suitPlanner.startup()

class CogHQAI(PlaceAI):
    lobbyZone = None
    suitZones = []
    elevatorZones = []
    numExtDoors = 0

    def __init__(self, air, zone_id, facilityMgr):
        PlaceAI.__init__(self, air, zone_id)

        self.wantSuits = True
        self.suitPlanners = []
        self.facilityMgr = facilityMgr

    def create(self):
        for zoneId in self.suitZones:
            if zoneId in DNA_MAP:
                self.dna[zoneId], self.storage[zoneId] = load_dna_file('dna/files/' + DNA_MAP[zoneId])

    def startup(self):
        self.active = True
        if self.wantSuits:
            for zone_id in self.suitZones:
                suitPlanner = DistributedSuitPlannerAI(self.air, self, zone_id)
                suitPlanner.generateWithRequired(zone_id)
                suitPlanner.startup()
                self.suitPlanners.append(suitPlanner)

        extDoors = []

        for i in range(self.numExtDoors):
            extDoor = DistributedCogHQDoorAI(self.air, i, DoorTypes.EXT_COGHQ, i, self.lobbyZone)
            extDoors.append(extDoor)

        for suitPlanner in self.suitPlanners:
            if suitPlanner.zoneId == self.zoneId:
                suitPlanner.cogHQDoors = extDoors

        intDoor = DistributedCogHQDoorAI(self.air, 0, DoorTypes.INT_COGHQ, 0, self.zoneId)

        for extDoor in extDoors:
            extDoor.setOtherDoor(intDoor)
            extDoor.zoneId = self.zoneId
            extDoor.generateWithRequired(self.zoneId)
            extDoor.sendUpdate('setDoorIndex', [extDoor.getDoorIndex()])

        intDoor.generateWithRequired(self.lobbyZone)
        intDoor.sendUpdate('setDoorIndex', [intDoor.getDoorIndex()])

class SBHQHoodAI(CogHQAI):
    zoneId = SellbotHQ
    lobbyZone = SellbotLobby
    suitZones = [SellbotHQ, SellbotFactoryExt]
    numExtDoors = 4

    def __init__(self, air, facilityMgr):
        CogHQAI.__init__(self, air, self.zoneId, facilityMgr)

class CBHQHoodAI(CogHQAI):
    zoneId = CashbotHQ
    lobbyZone = CashbotLobby
    suitZones = [CashbotHQ]

    def __init__(self, air, facilityMgr):
        CogHQAI.__init__(self, air, self.zoneId, facilityMgr)

class LBHQHoodAI(CogHQAI):
    zoneId = LawbotHQ
    lobbyZone = BossbotLobby
    suitZones = [LawbotHQ]

    def __init__(self, air, facilityMgr):
        CogHQAI.__init__(self, air, self.zoneId, facilityMgr)

class BBHQHoodAI(CogHQAI):
    zoneId = BossbotHQ
    lobbyZone = BossbotLobby

    def __init__(self, air, facilityMgr):
        CogHQAI.__init__(self, air, self.zoneId, facilityMgr)

class PlaygroundAI(SafeZoneAI):
    treasurePlannerClass: Optional[Type[RegenTreasurePlanner]] = None

    def __init__(self, air, zone_id):
        SafeZoneAI.__init__(self, air, zone_id)
        self.npcs = []
        self.butterflies = []
        self.trolley: Optional[DistributedTrolleyAI] = None
        self.treasurePlanner: Optional[RegenTreasurePlanner] = None

    def create(self):
        super().create()

        self.npcs = NPCToons.createNpcsInZone(self.air, self.zone_id)
        # TODO: trolley, butterflys, disney npc
        self.trolley = DistributedTrolleyAI(self.air)
        self.trolley.generateWithRequired(self.zone_id)

        if self.treasurePlannerClass is not None:
            self.treasurePlanner = self.treasurePlannerClass(self.zone_id)
            self.treasurePlanner.start()

    def createButterflies(self, playground):
        ButterflyGlobals.generateIndexes(self.zone_id, playground)
        for i in range(0, ButterflyGlobals.NUM_BUTTERFLY_AREAS[playground]):
            for _ in range(0, ButterflyGlobals.NUM_BUTTERFLIES[playground]):
                butterfly = DistributedButterflyAI(self.air, playground, i, self.zone_id)
                butterfly.request('Off')
                butterfly.generateWithRequired(self.zone_id)
                butterfly.start()
                self.butterflies.append(butterfly)

class HoodAI:
    zoneId = None

    def __init__(self, air):
        self.playground = PlaygroundAI(air, self.zoneId)
        self.streets: List[StreetAI] = [StreetAI(air, branchId) for branchId in HoodHierarchy[self.zoneId]]

    def startup(self):
        self.playground.active = True
        for street in self.streets:
            street.active = True

    def shutdown(self):
        self.playground.active = False
        for street in self.streets:
            street.active = False

class DDHoodAI(HoodAI):
    zoneId = DonaldsDock

    def startup(self):
        self.playground.treasurePlannerClass = DDTreasurePlanner
        super().startup()

class TTHoodAI(HoodAI):
    zoneId = ToontownCentral

    def startup(self):
        self.playground.treasurePlannerClass = TTTreasurePlanner
        self.playground.createButterflies(ButterflyGlobals.TTC)
        for street in self.streets:
            street.wantSuits = True
        super().startup()

class BRHoodAI(HoodAI):
    zoneId = TheBrrrgh

    def startup(self):
        self.playground.treasurePlannerClass = BRTreasurePlanner
        super().startup()

class MMHoodAI(HoodAI):
    zoneId = MinniesMelodyland

    def startup(self):
        self.playground.treasurePlannerClass = MMTreasurePlanner
        super().startup()

class DGHoodAI(HoodAI):
    zoneId = DaisyGardens

    def startup(self):
        self.playground.treasurePlannerClass = DGTreasurePlanner
        self.playground.createButterflies(ButterflyGlobals.DG)
        super().startup()

class DLHoodAI(HoodAI):
    zoneId = DonaldsDreamland

    def startup(self):
        self.playground.treasurePlannerClass = DLTreasurePlanner
        super().startup()