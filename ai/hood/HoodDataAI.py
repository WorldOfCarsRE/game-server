from ai.globals.HoodGlobals import *
from typing import List, Dict, Union, Optional
from ai.DistributedObjectAI import DistributedObjectAI
from panda3d.toontown import loadDNAFileAI, DNAStorage, DNAData, DNAGroup
from ai.toon import NPCToons
from ai.safezone import ButterflyGlobals
from ai.safezone.DistributedButterflyAI import DistributedButterflyAI
from ai.trolley.DistributedTrolleyAI import DistributedTrolleyAI
from ai.suit.DistributedSuitPlannerAI import DistributedSuitPlannerAI
from ai.coghq.DistributedFactoryElevatorExtAI import DistributedFactoryElevatorExtAI
from .Treasures import *
from ai.building.ElevatorLaffMinimums import *
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
    def __init__(self, air, zoneId):
        self.air = air
        self.zoneId: int = zoneId

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

    def __init__(self, air, zoneId):
        PlaceAI.__init__(self, air, zoneId)
        self.buildings: Dict[int, object] = {}
        self.hq: Union[HQBuildingAI, None] = None
        self.gagShop: Union[GagshopBuildingAI, None] = None
        self.dnaStore: DNAStorage = None
        self.dnaData: DNAData = None

    @staticmethod
    def getInteriorZone(zoneId, block):
        return zoneId - zoneId % 100 + 500 + block

    def create(self):
        self.dnaStore = DNAStorage()
        self.dnaData = loadDNAFileAI(self.dnaStore, 'dna/' + DNA_MAP[self.zoneId])

        for i in range(self.dnaStore.getNumBlockNumbers()):
            blockNumber = self.dnaStore.getBlockNumberAt(i)
            buildingType = self.dnaStore.getBlockBuildingType(blockNumber)
            interiorZone = self.getInteriorZone(self.zoneId, blockNumber)
            exteriorZone = self.dnaStore.getZoneFromBlockNumber(blockNumber)

            if buildingType == 'hq':
                self.buildings[blockNumber] = HQBuildingAI(self.air, exteriorZone, interiorZone, blockNumber)
            elif buildingType == 'gagshop':
                self.buildings[blockNumber] = GagshopBuildingAI(self.air, exteriorZone, interiorZone, blockNumber)
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
                bldg.block = blockNumber
                bldg.exteriorZoneId = exteriorZone
                bldg.interiorZoneId = self.getInteriorZone(exteriorZone, blockNumber)
                bldg.generateWithRequired(self.zoneId)
                bldg.request('Toon')
                self.buildings[blockNumber] = bldg

        for i in range(self.dnaStore.getNumDNAVisGroupsAI()):
            visGroup = self.dnaStore.getDNAVisGroupAI(i)
            zone = int(visGroup.name.split(':')[0])

            visibles = []
            for x in range(visGroup.getNumVisibles()):
                zoneId = int(visGroup.getVisibleName(x).split(':')[0])
                visibles.append(zoneId)
            if self.zoneId not in visibles:
                visibles.append(self.zoneId)

            self.air.vismap[zone] = tuple(visibles)

        fPonds, fGroups = self.air.findFishingPonds(self.dnaData, self.zoneId, self.zoneId)

        for pond, group in zip(fPonds, fGroups):
            fSpots = self.air.findFishingSpots(pond, group)

class StreetAI(SafeZoneAI):
    def __init__(self, air, zoneId):
        SafeZoneAI.__init__(self, air, zoneId)

        self.wantSuits = False
        self.suitPlanner: Optional[DistributedSuitPlannerAI] = None

    def create(self):
        super().create()

        # TODO: suits
        if self.wantSuits:
            self.suitPlanner = DistributedSuitPlannerAI(self.air, self.dnaStore, self.zoneId)
            self.suitPlanner.generateWithRequired(self.zoneId)
            self.suitPlanner.startup()

class CogHQAI(PlaceAI):
    lobbyZone = None
    suitZones = []
    elevatorZones = []
    numExtDoors = 0

    def __init__(self, air, zoneId, facilityMgr):
        PlaceAI.__init__(self, air, zoneId)

        self.wantSuits = True
        self.suitPlanners = []
        self.facilityMgr = facilityMgr

        self.zone2Dna = {}
        self.zone2Storage = {}

    def create(self):
        for zoneId in self.suitZones:
            if zoneId in DNA_MAP:
                dnaStore = DNAStorage()
                dnaData = loadDNAFileAI(dnaStore, 'dna/' + DNA_MAP[self.zoneId])

                self.zone2Dna[zoneId] = dnaData
                self.zone2Storage[zoneId] = dnaStore

    def startup(self):
        self.active = True
        if self.wantSuits:
            for zoneId in self.suitZones:
                suitPlanner = DistributedSuitPlannerAI(self.air, self.zone2Storage[zoneId], zoneId)
                suitPlanner.generateWithRequired(zoneId)
                suitPlanner.startup()
                self.suitPlanners.append(suitPlanner)

        self.createElevators()

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

    def createElevators(self):
        pass

class SBHQHoodAI(CogHQAI):
    zoneId = SellbotHQ
    lobbyZone = SellbotLobby
    suitZones = [SellbotHQ, SellbotFactoryExt]
    numExtDoors = 4

    def __init__(self, air, facilityMgr):
        CogHQAI.__init__(self, air, self.zoneId, facilityMgr)

    def createElevators(self):
        elevator0 = DistributedFactoryElevatorExtAI(self.air, self.air.factoryMgr, SellbotFactoryInt,
                      0, antiShuffle = 0, minLaff = FactoryLaffMinimums[0])
        elevator0.generateWithRequired(SellbotFactoryExt)

        elevator1 = DistributedFactoryElevatorExtAI(self.air, self.air.factoryMgr, SellbotFactoryInt,
                      1, antiShuffle = 0, minLaff = FactoryLaffMinimums[1])
        elevator1.generateWithRequired(SellbotFactoryExt)

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

    def __init__(self, air, zoneId):
        SafeZoneAI.__init__(self, air, zoneId)
        self.npcs = []
        self.butterflies = []
        self.trolley: Optional[DistributedTrolleyAI] = None
        self.treasurePlanner: Optional[RegenTreasurePlanner] = None

    def create(self):
        super().create()

        self.npcs = NPCToons.createNpcsInZone(self.air, self.zoneId)
        # TODO: trolley, butterflys, disney npc
        self.trolley = DistributedTrolleyAI(self.air)
        self.trolley.generateWithRequired(self.zoneId)

        if self.treasurePlannerClass is not None:
            self.treasurePlanner = self.treasurePlannerClass(self.zoneId)
            self.treasurePlanner.start()

    def createButterflies(self, playground):
        ButterflyGlobals.generateIndexes(self.zoneId, playground)
        for i in range(0, ButterflyGlobals.NUM_BUTTERFLY_AREAS[playground]):
            for _ in range(0, ButterflyGlobals.NUM_BUTTERFLIES[playground]):
                butterfly = DistributedButterflyAI(self.air, playground, i, self.zoneId)
                butterfly.request('Off')
                butterfly.generateWithRequired(self.zoneId)
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