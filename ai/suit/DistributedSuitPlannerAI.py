from ai.DistributedObjectAI import DistributedObjectAI

from dataclasses import dataclass
from dataslots import with_slots
from typing import List, Tuple, Dict

from ai.globals.HoodGlobals import *
from panda3d.core import Point3

from direct.task import Task

@with_slots
@dataclass
class SuitHoodInfo:
    zoneId: int
    minSuits: int
    maxSuits: int
    minSuitBldgs: int
    maxSuitBldgs: int
    buildingWeight: int
    maxBattleSuits: int
    joinChances: Tuple[int]
    deptChances: Tuple[int]
    levels: Tuple[int]
    buildingDifficulties: Tuple[int]

SUIT_HOOD_INFO = {
    SillyStreet: SuitHoodInfo(zoneId=SillyStreet, minSuits=5, maxSuits=15, minSuitBldgs=0, maxSuitBldgs=5, buildingWeight=20,
                              maxBattleSuits=3, joinChances=(1, 5, 10, 40, 60, 80), deptChances=(25, 25, 25, 25),
                              levels=(1, 2, 3), buildingDifficulties=()),
    LoopyLane: SuitHoodInfo(zoneId=SillyStreet, minSuits=3, maxSuits=10, minSuitBldgs=0, maxSuitBldgs=5,
                            buildingWeight=15, maxBattleSuits=3, joinChances=(1, 5, 10, 40, 60, 80),
                            deptChances=(10, 70, 10, 10), levels=(1, 2, 3), buildingDifficulties=()),
    PunchlinePlace: SuitHoodInfo(zoneId=PunchlinePlace, minSuits=3, maxSuits=10, minSuitBldgs=0, maxSuitBldgs=5,
                                 buildingWeight=15, maxBattleSuits=3, joinChances=(1, 5, 10, 40, 60, 80),
                                 deptChances=(10, 10, 40, 40), levels=(1, 2, 3), buildingDifficulties=()),
    SellbotHQ: SuitHoodInfo(zoneId=SellbotHQ, minSuits=3, maxSuits=15, minSuitBldgs=0, maxSuitBldgs=0, buildingWeight=0,
                            maxBattleSuits=4, joinChances= (1, 5, 10, 40, 60, 80), deptChances=(0, 0, 0, 100),
                            levels=(4, 5, 6), buildingDifficulties=()),
    SellbotFactoryExt: SuitHoodInfo(zoneId=SellbotFactoryExt, minSuits=10, maxSuits=20, minSuitBldgs=0, maxSuitBldgs=0, buildingWeight=0,
                            maxBattleSuits=4, joinChances= (1, 5, 10, 40, 60, 80), deptChances=(0, 0, 0, 100),
                            levels=(4, 5, 6), buildingDifficulties=()),
    CashbotHQ: SuitHoodInfo(zoneId=CashbotHQ, minSuits=10, maxSuits=20, minSuitBldgs=0, maxSuitBldgs=0, buildingWeight=0,
                            maxBattleSuits=4, joinChances= (1, 5, 10, 40, 60, 80), deptChances=(0, 0, 100, 0),
                            levels=(7, 8, 9), buildingDifficulties=()),
    LawbotHQ: SuitHoodInfo(zoneId=LawbotHQ, minSuits=10, maxSuits=20, minSuitBldgs=0, maxSuitBldgs=0, buildingWeight=0,
                            maxBattleSuits=4, joinChances= (1, 5, 10, 40, 60, 80), deptChances=(0, 100, 0, 0),
                            levels=(8, 9, 10), buildingDifficulties=()),
}

from panda3d.toontown import DNASuitPoint
from .SuitTimings import fromSky, suitWalkSpeed

import random
from typing import Optional

from ai.suit.DistributedSuitAI import DistributedSuitAI, SuitDNA
from ai.suit.SuitGlobals import SuitDept, SuitHeads, pickFromFreqList

UPKEEP_DELAY = 10
ADJUST_DELAY = 300
PATH_COLLISION_BUFFER = 5

MIN_PATH_LEN = 40
MAX_PATH_LEN = 300
MAX_SUIT_TIER = 5

class DistributedSuitPlannerAI(DistributedObjectAI):
    def __init__(self, air, dnaStore, zoneId):
        DistributedObjectAI.__init__(self, air)
        self.dnaStore = dnaStore
        self.zoneId = zoneId
        self.info: SuitHoodInfo = SUIT_HOOD_INFO[zoneId]
        self.battleMgr: BattleManagerAI = BattleManagerAI(self.air)

        self.zone2battlePos: Dict[int, Point3] = {}

        for i in range(self.dnaStore.getNumDNAVisGroupsAI()):
            visGroup = self.dnaStore.getDNAVisGroupAI(i)
            visZone = int(visGroup.name)
            numBattleCells = visGroup.getNumBattleCells()

            if not numBattleCells:
                print('zone has no battle cells: %d' % visZone)
                continue

            self.zone2battlePos[visZone] = visGroup.getBattleCell(0).getPos()

            if numBattleCells > 1:
                print('Multiple battle cells for zoneId: %d' % visZone)

        self.streetPoints: List[DNASuitPoint] = []
        self.frontDoorPoints: List[DNASuitPoint] = []
        self.sideDoorPoints: List[DNASuitPoint] = []
        self.cogHQDoorPoints: List[DNASuitPoint] = []
        self.cogHQDoors = []
        self.pointIndexes = {}

        numPoints = self.dnaStore.getNumSuitPoints()
        for i in range(numPoints):
            suitPoint = self.dnaStore.getSuitPointAtIndex(i)
            pointType = suitPoint.getPointType()
            if pointType == DNASuitPoint.STREET_POINT:
                self.streetPoints.append(suitPoint)
            elif pointType == DNASuitPoint.FRONT_DOOR_POINT:
                self.frontDoorPoints.append(suitPoint)
            elif pointType == DNASuitPoint.SIDE_DOOR_POINT:
                self.sideDoorPoints.append(suitPoint)
            elif pointType == DNASuitPoint.COGHQ_IN_POINT or pointType == DNASuitPoint.COGHQ_OUT_POINT:
                self.cogHQDoorPoints.append(suitPoint)

            self.pointIndexes[suitPoint.getIndex()] = suitPoint

        self.suits: List[DistributedSuitAI] = []
        self.baseNumSuits = (self.info.maxSuits + self.info.minSuits) // 2
        self.popAdjustment = 0
        self.numFlyInSuits = 0
        self.suitWalkSpeed = suitWalkSpeed

    def getZoneId(self):
        return self.zoneId

    def genPath(self, startPoint, endPoint, minPathLen, maxPathLen):
        return self.dnaStore.getSuitPath(startPoint, endPoint, minPathLen, maxPathLen)

    def startup(self):
        self.upkeep()
        self.adjust()

    def createNewSuit(self):
        streetPoints = list(range(len(self.streetPoints)))
        random.shuffle(streetPoints)

        startPoint = None

        while startPoint is None and streetPoints:
            point = self.streetPoints[streetPoints.pop()]

            if not self.pointCollision(point, None, fromSky):
                startPoint = point

        if startPoint is None:
            print('start pt is none')
            return False

        suit = DistributedSuitAI(self.air, self)
        suit.startPoint = startPoint
        suit.flyInSuit = 1

        if not self.chooseDestination(suit, fromSky):
            print(f'({self.zoneId}) failed to choose destination')
            suit.delete()
            return False

        level = random.choice(self.info.levels)
        if (level - 5) < 0:
            tierMin = 0
        else:
            tierMin = level - 5
        if (level - 1) < MAX_SUIT_TIER:
            tierMax = level - 1
        else:
            tierMax = MAX_SUIT_TIER

        tier = random.choice([tierMin, tierMax])
        department = pickFromFreqList(self.info.deptChances)
        head = SuitHeads.at(department * 8 + tier)
        suit.dna = SuitDNA(type='s', head=head, dept=SuitDept(department).char)
        suit.actualLevel = level
        suit.initializePath()
        suit.generateWithRequired(suit.zoneId)
        suit.moveToNextLeg(None)
        self.suits.append(suit)
        self.numFlyInSuits += 1
        return True

    def upkeep(self, task=None):
        desired = self.baseNumSuits + self.popAdjustment
        desired = min(desired, self.info.maxSuits)
        deficit = (desired - self.numFlyInSuits + 3) / 4
        while deficit > 0:
            if not self.createNewSuit():
                break
            deficit -= 1

        t = random.random() * 2.0 + UPKEEP_DELAY
        taskMgr.doMethodLater(t, self.upkeep, self.uniqueName('upkeep-suits'))

    def adjust(self, task=None):
        if self.info.maxSuits == 0:
            return Task.done

        adjustment = random.choice((-2, -1, -1, 0, 0, 0, 1, 1, 2))
        self.popAdjustment += adjustment

        desired = self.baseNumSuits + self.popAdjustment

        if desired < self.info.minSuits:
            self.popAdjustment = self.info.minSuits - self.baseNumSuits
        elif desired > self.info.maxSuits:
            self.popAdjustment = self.info.maxSuits - self.baseNumSuits

        t = random.random() * 2.0 + ADJUST_DELAY
        taskMgr.doMethodLater(t, self.upkeep, self.uniqueName('adjust-suits'))

    def pointCollision(self, point, adjacentPoint, elapsedTime):
        for suit in self.suits:
            if suit.pointInMyPath(point, elapsedTime, PATH_COLLISION_BUFFER):
                return True

        if adjacentPoint is not None:
            return self.battleCollision(point, adjacentPoint)
        else:
            adjacentPoints = self.dnaStore.getAdjacentPoints(point)
            i = adjacentPoints.getNumPoints() - 1
            while i >= 0:
                pi = adjacentPoints.getPointIndex(i)
                adjacentPoint = self.pointIndexes[pi]
                i -= 1

                if self.battleCollision(point, adjacentPoint):
                    return True

        return False

    def battleCollision(self, point, adjacentPoint):
        zone = self.dnaStore.getSuitEdgeZone(point.getIndex(), adjacentPoint.getIndex())
        return self.battleMgr.cellHasBattle(zone)

    def pathCollision(self, path: List[int], elapsedTime):
        pathLength = path.getNumPoints()

        i = 0
        assert i < pathLength
        pi = path.getPointIndex(i)
        point = self.pointIndexes[pi]

        adjacentPoint = self.pointIndexes[path.getPointIndex(i + 1)]

        while point.getPointType() == DNASuitPoint.FRONTDOORPOINT or \
              point.getPointType() == DNASuitPoint.SIDEDOORPOINT:
            i += 1
            assert i < pathLength

            lastPi = pi
            pi = path.getPointIndex(i)
            adjacentPoint = point
            point = self.pointIndexes[pi]

            elapsedTime += self.dnaStore.getSuitEdgeTravelTime(
                lastPi, pi, self.suitWalkSpeed)

        return self.pointCollision(point, adjacentPoint, elapsedTime)

    def chooseDestination(self, suit: DistributedSuitAI, startTime):
        streetPoints = list(range(len(self.streetPoints)))
        random.shuffle(streetPoints)

        retries = 0
        while streetPoints and retries < 50:
            endPoint = self.streetPoints[streetPoints.pop()]

            path = self.genPath(suit.startPoint, endPoint, MIN_PATH_LEN, MAX_PATH_LEN)

            if path and not self.pathCollision(path, startTime):
                suit.endPoint = endPoint
                # print('CHOSEN PATH:', suit.startPoint, endPoint, path)
                suit.path = path
                return 1

            retries += 1

    def removeSuit(self, suit: DistributedSuitAI):
        suit.requestDelete()
        self.suits.remove(suit)
        if suit.flyInSuit:
            self.numFlyInSuits -= 1

    def requestBattle(self, zoneId, suit: DistributedSuitAI, toonId) -> bool:
        pos = self.zone2battlePos[zoneId]

        battle = self.battleMgr.newBattle(suit, toonId, zoneId, zoneId, pos)
        return True

    def __battleFinished(self):
        pass

class BattleManagerAI:
    BATTLE_CONSTRUCTOR = None
    __slots__ = 'air', 'cell2Battle'

    def __init__(self, air):
        self.air = air
        self.cell2Battle: Dict[int, object] = {}

    def newBattle(self, suit, toonId, cellId, zoneId, pos):
        from ai.battle import DistributedBattleAI

        if cellId in self.cell2Battle:
            if not self.requestBattleAddSuit(cellId, suit):
                suit.flyAwayNow()

            battle = self.cell2Battle[cellId]
            battle.signupToon(toonId, pos[0], pos[1], pos[2])
        else:
            battle = DistributedBattleAI(self.air, self, pos, suit, toonId, zoneId)
            battle.generateWithRequired(zoneId)
            battle.battleCellId = cellId
            self.cell2Battle[cellId] = battle

        return battle

    def removeBattle(self, cellId):
        if cellId in self.cell2Battle:
            self.cell2Battle[cellId].requestDelete()
            del self.cell2Battle[cellId]

    def requestBattleAddSuit(self, cellId, suit):
        return self.cell2Battle[cellId].suitRequestJoin(suit)

    def cellHasBattle(self, cellId):
        return cellId in self.cell2Battle