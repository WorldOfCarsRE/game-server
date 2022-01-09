from ai.DistributedObjectAI import DistributedObjectAI

from .DistributedToonInteriorAI import DistributedToonInteriorAI, DistributedToonHallInteriorAI
from .DistributedDoorAI import DistributedDoorAI, BUILDING_TAKEOVER

from ai.toon import NPCToons
from ai.globals.HoodGlobals import ToonHall

from direct.fsm.FSM import FSM

from . import DoorTypes
from . import CogBuildingGlobalsAI
from ai.building.DistributedElevatorExtAI import DistributedElevatorExtAI
from ai.building.DistributedKnockKnockDoorAI import DistributedKnockKnockDoorAI
import time, random

CLEAR_OUT_TOON_BLDG_TIME = 4
TO_SUIT_BLDG_TIME = 8
VICTORY_SEQUENCE_TIME = 11

class BuildingBase(object):

    def isHQ(self):
        return 0

class DistributedBuildingAI(DistributedObjectAI, FSM, BuildingBase):
    defaultTransitions = {
            'Off': ['WaitForVictors', 'BecomingToon', 'Toon', 'ClearOutToonInterior', 'BecomingSuit', 'Suit'],
            'WaitForVictors': ['BecomingToon'],
            'BecomingToon': ['Toon', ],
            'Toon': ['ClearOutToonInterior'],
            'ClearOutToonInterior': ['BecomingSuit'],
            'BecomingSuit': ['Suit'],
            'Suit': ['WaitForVictors', 'BecomingToon'],
    }

    def __init__(self, air, hoodData):
        DistributedObjectAI.__init__(self, air)
        FSM.__init__(self, 'DistributedBuildingAI')

        # hoodData appears both on here and suit planner.
        # this is going to need a refactor...
        self.hoodData = hoodData

        self.block = 0
        self.track = 'c'
        self.difficulty = 1
        self.numFloors = 1
        self.interiorZoneId = 0
        self.exteriorZoneId = 0

        self.door = None
        self.insideDoor = None
        self.interior = None
        self.elevator = None
        self.npcs = []
        self.becameSuitTime = 0

    def getBlock(self):
        return [self.block, self.interiorZoneId]

    def getTrack(self):
        return self.track

    def getSuitData(self):
        return ord(self.track), self.difficulty, self.numFloors

    def d_setState(self, state):
        state = state[0].lower() + state[1:]
        self.sendUpdate('setState', [state, globalClockDelta.getRealNetworkTime()])

    def getState(self):
        state = self.state[0].lower() + self.state[1:]
        return [state, globalClockDelta.getRealNetworkTime()]

    def isSuitState(self):
        return self.getState()[0] == 'suit'

    def enterBecomingToon(self):
        self.d_setState('becomingToon')

        taskMgr.doMethodLater(
            VICTORY_SEQUENCE_TIME,
            self.becomingToonTask,
            str(self.block)+'_becomingToon-timer')

    def becomingToonTask(self, task):
        self.demand('Toon')

        # save bldg state
        return task.done
    
    def exitBecomingToon(self):
        taskMgr.remove(str(self.block)+'_becomingToon-timer')
        self.trackToonBlock()
        self.detrackSuitBlock()

    def enterToon(self):
        self.d_setState('toon')

        if self.interiorZoneId == ToonHall:
            self.interior = DistributedToonHallInteriorAI(self.air)
        else:
            self.interior = DistributedToonInteriorAI(self.air)

        self.interior.block = self.block
        self.interior.zoneId = self.interiorZoneId
        self.interior.generateWithRequired(self.interiorZoneId)

        door = DistributedDoorAI(self.air, self.block, DoorTypes.EXT_STANDARD)
        door.zoneId = self.exteriorZoneId

        insideDoor = DistributedDoorAI(self.air, self.block, DoorTypes.INT_STANDARD)
        insideDoor.zoneId = self.interiorZoneId

        door.setOtherDoor(insideDoor)
        insideDoor.setOtherDoor(door)

        door.generateWithRequired(self.exteriorZoneId)
        insideDoor.generateWithRequired(self.interiorZoneId)

        self.door = door
        self.insideDoor = insideDoor

        self.npcs = NPCToons.createNpcsInZone(self.air, self.interiorZoneId)

        self.becameSuitTime = 0
        self.knockKnock = DistributedKnockKnockDoorAI(self.air, self.block)
        self.knockKnock.generateWithRequired(self.exteriorZoneId)

    def exitToon(self):
        self.door.setDoorLock(BUILDING_TAKEOVER)

    def enterClearOutToonInterior(self):
        self.d_setState('clearOutToonInterior')
        if hasattr(self, 'interior'):
            self.interior.demand('BeingTakenOver')

        taskMgr.doMethodLater(
            CLEAR_OUT_TOON_BLDG_TIME,
            self.clearOutToonInteriorTask,
            f'{self.block}_clearOutToonInterior-timer')

        self.detrackToonBlock()
        self.trackSuitBlock()

    def clearOutToonInteriorTask(self, task):
        self.demand('BecomingSuit')
        return task.done

    def exitClearOutToonInterior(self):
        taskMgr.remove(f'{self.block}_clearOutToonInterior-timer')

    def getMinMaxFloors(self, difficulty):
        return CogBuildingGlobalsAI.CogBuildingInfo[difficulty].floors

    def suitTakeOver(self, track, difficulty, buildingHeight):
        # not toon block check here
        # update saved by
        maxDifficulty = len(CogBuildingGlobalsAI.CogBuildingInfo) - 1
        if difficulty > maxDifficulty:
            difficulty = maxDifficulty

        minFloors, maxFloors = self.getMinMaxFloors(difficulty)

        if buildingHeight == None:
            numFloors = random.randint(minFloors, maxFloors)
        else:
            numFloors = buildingHeight + 1
 
            if (numFloors < minFloors or numFloors > maxFloors):
                numFloors = random.randint(minFloors, maxFloors)

        self.track = track
        self.difficulty = difficulty
        self.numFloors = numFloors
        self.becameSuitTime = time.time()
        print(f'hot tub at {self.zoneId}')
        self.demand('ClearOutToonInterior')

    def toonTakeOver(self):
        # self.demand('BecomingToonFromCogdo')
        self.demand('BecomingToon')
        #self.hoodData.suitPlanner.recycleBuilding()
        if hasattr(self, "interior"):
            self.interior.requestDelete()
            del self.interior
        
    def enterBecomingSuit(self):
        self.sendUpdate('setSuitData',
            [ord(self.track), self.difficulty, self.numFloors])

        self.d_setState('becomingSuit')

        taskMgr.doMethodLater(
            TO_SUIT_BLDG_TIME,
            self.becomingSuitTask,
            f'{self.block}_becomingSuit-timer')

    def becomingSuitTask(self, task):
        self.demand('Suit')

        # save goes here

        return task.done

    def exitBecomingSuit(self):
        taskMgr.remove(f'{self.block}_becomingSuit-timer')
        if hasattr(self, 'interior'):
            self.interior.requestDelete()
            del self.interior
            self.door.requestDelete()
            del self.door
            self.insideDoor.requestDelete()
            del self.insideDoor
            self.knockKnock.requestDelete()
            del self.knockKnock

    def enterSuit(self):
        self.sendUpdate('setSuitData',
            [ord(self.track), self.difficulty, self.numFloors])

        # self.planner = SuitPlannerInteriorAI(self.numFloors, self.difficulty, self.track, self.interiorZoneId)

        self.d_setState('suit')

        self.elevator = DistributedElevatorExtAI(self.air, self)
        self.elevator.generateWithRequired(self.exteriorZoneId)
        
    def trackToonBlock(self):
        if self.block not in self.hoodData.toonBlocks:
            self.hoodData.toonBlocks.append(self.block)

    def detrackToonBlock(self):
        if self.block in self.hoodData.toonBlocks:
            self.hoodData.toonBlocks.remove(self.block)

    def trackSuitBlock(self):
        if self.block not in self.hoodData.suitBlocks:
            self.hoodData.suitBlocks.append(self.block)

    def detrackSuitBlock(self):
        if self.block in self.hoodData.suitBlocks:
            self.hoodData.suitBlocks.remove(self.block)

    def exitSuit(self):
        # del self.planner
        if hasattr(self, 'elevator'):
            self.elevator.requestDelete()
            del self.elevator
        self.detrackSuitBlock()
