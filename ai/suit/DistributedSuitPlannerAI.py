from ai.DistributedObjectAI import DistributedObjectAI

from dataclasses import dataclass
from dataslots import with_slots
from typing import List, Tuple, Dict

from ai.building import CogBuildingGlobalsAI
from ai.globals.HoodGlobals import *
from ai.toon import NPCToons
from panda3d.core import Point3

from direct.task import Task

import time

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
    LoopyLane: SuitHoodInfo(zoneId=LoopyLane, minSuits=3, maxSuits=10, minSuitBldgs=0, maxSuitBldgs=5,
                            buildingWeight=15, maxBattleSuits=3, joinChances=(1, 5, 10, 40, 60, 80),
                            deptChances=(10, 70, 10, 10), levels=(1, 2, 3), buildingDifficulties=()),
    PunchlinePlace: SuitHoodInfo(zoneId=PunchlinePlace, minSuits=3, maxSuits=10, minSuitBldgs=0, maxSuitBldgs=5,
                                 buildingWeight=15, maxBattleSuits=3, joinChances=(1, 5, 10, 40, 60, 80),
                                 deptChances=(10, 10, 40, 40), levels=(1, 2, 3), buildingDifficulties=()),
    BarnacleBoulevard: SuitHoodInfo(zoneId=BarnacleBoulevard, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99, buildingWeight=100,
                              maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80), deptChances=(90, 10, 0, 0),
                              levels=(2, 3, 4), buildingDifficulties=()),
    SeaweedStreet: SuitHoodInfo(zoneId=SeaweedStreet, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99,
                            buildingWeight=100, maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80),
                            deptChances=(0, 0, 90, 10), levels=(3, 4, 5, 6), buildingDifficulties=()),
    LighthouseLane: SuitHoodInfo(zoneId=LighthouseLane, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99,
                                 buildingWeight=100, maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80),
                                 deptChances=(40, 40, 10, 10), levels=(3, 4, 5, 6), buildingDifficulties=()),
    ElmStreet: SuitHoodInfo(zoneId=ElmStreet, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99, buildingWeight=100,
                              maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80), deptChances=(0, 20, 10, 70),
                              levels=(2, 3, 4), buildingDifficulties=()),
    MapleStreet: SuitHoodInfo(zoneId=MapleStreet, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99,
                            buildingWeight=100, maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80),
                            deptChances=(10, 70, 0, 20), levels=(3, 4, 5, 6), buildingDifficulties=()),
    OakStreet: SuitHoodInfo(zoneId=OakStreet, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99,
                                 buildingWeight=100, maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80),
                                 deptChances=(5, 5, 5, 85), levels=(3, 4, 5, 6), buildingDifficulties=()),
    AltoAvenue: SuitHoodInfo(zoneId=AltoAvenue, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99, buildingWeight=100,
                              maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80), deptChances=(0, 0, 50, 50),
                              levels=(2, 3, 4), buildingDifficulties=()),
    BaritoneBoulevard: SuitHoodInfo(zoneId=BaritoneBoulevard, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99,
                            buildingWeight=100, maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80),
                            deptChances=(0, 0, 90, 10), levels=(3, 4, 5, 6), buildingDifficulties=()),
    TenorTerrace: SuitHoodInfo(zoneId=TenorTerrace, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99,
                                 buildingWeight=100, maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80),
                                 deptChances=(50, 50, 0, 0), levels=(3, 4, 5, 6), buildingDifficulties=()),
    WalrusWay: SuitHoodInfo(zoneId=WalrusWay, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99, buildingWeight=100,
                              maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80), deptChances=(90, 10, 0, 0),
                              levels=(5, 6, 7), buildingDifficulties=()),
    SleetStreet: SuitHoodInfo(zoneId=SleetStreet, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99,
                            buildingWeight=100, maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80),
                            deptChances=(10, 20, 30, 40), levels=(5, 6, 7), buildingDifficulties=()),
    PolarPlace: SuitHoodInfo(zoneId=PolarPlace, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99,
                                 buildingWeight=100, maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80),
                                 deptChances=(5, 85, 5, 5), levels=(7, 8, 9), buildingDifficulties=()),
    LullabyLane: SuitHoodInfo(zoneId=LullabyLane, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99,
                            buildingWeight=100, maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80),
                            deptChances=(25, 25, 25, 25), levels=(6, 7, 8, 9), buildingDifficulties=()),
    PajamaPlace: SuitHoodInfo(zoneId=PajamaPlace, minSuits=1, maxSuits=5, minSuitBldgs=0, maxSuitBldgs=99,
                                 buildingWeight=100, maxBattleSuits=4, joinChances=(1, 5, 10, 40, 60, 80),
                                 deptChances=(5, 5, 85, 5), levels=(6, 7, 8, 9), buildingDifficulties=()),                                 
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
from .SuitTimings import fromSky, fromSuitBuilding, suitWalkSpeed

import random
from typing import Optional

from ai.suit.DistributedSuitAI import DistributedSuitAI, SuitDNA
from ai.suit.SuitGlobals import suitDepts, SuitDept, SuitHeads, pickFromFreqList

UPKEEP_DELAY = 10
ADJUST_DELAY = 300
PATH_COLLISION_BUFFER = 5

MIN_TAKEOVER_PATH_LEN = 2
MIN_PATH_LEN = 40
MAX_PATH_LEN = 300
SUIT_BUILDING_NUM_SUITS = 1.5
SUIT_BUILDING_TIMEOUT = [None,
 None,
 None,
 None,
 None,
 None,
 72,
 60,
 48,
 36,
 24,
 12,
 6,
 3,
 1,
 0.5]
BUILDING_HEIGHT_DISTRIBUTION = [14, 18, 25, 23, 20]
TOTAL_SUIT_BUILDING_PCT = 18 # * CogDoPopFactor
MAX_SUIT_TIER = 5
MAX_BLDG_HEIGHT = 5

class DistributedSuitPlannerAI(DistributedObjectAI):
    def __init__(self, air, hoodData, dnaStore):
        DistributedObjectAI.__init__(self, air)
        self.hoodData = hoodData
        self.dnaStore = dnaStore
        self.zoneId = hoodData.zoneId
        
        self.air.suitPlanners[hoodData.zoneId] = self
        
        self.initBweight()        

        self.info: SuitHoodInfo = SUIT_HOOD_INFO[self.zoneId]
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
            if pointType == DNASuitPoint.STREETPOINT:
                self.streetPoints.append(suitPoint)
            elif pointType == DNASuitPoint.FRONTDOORPOINT:
                self.frontDoorPoints.append(suitPoint)
            elif pointType == DNASuitPoint.SIDEDOORPOINT:
                self.sideDoorPoints.append(suitPoint)
            elif pointType == DNASuitPoint.COGHQINPOINT or pointType == DNASuitPoint.COGHQOUTPOINT:
                self.cogHQDoorPoints.append(suitPoint)

            self.pointIndexes[suitPoint.getIndex()] = suitPoint

        self.suits: List[DistributedSuitAI] = []
        self.baseNumSuits = (self.info.maxSuits + self.info.minSuits) // 2
        self.popAdjustment = 0
        self.numFlyInSuits = 0
        self.numBuildingSuits = 0
        self.numAttemptingTakeover = 0
        self.suitWalkSpeed = suitWalkSpeed
        self.targetNumSuitBuildings = self.info.maxSuitBldgs
        self.pendingBuildingTracks = []
        self.pendingBuildingHeights = []
        self.initBuildingsAndPoints()
        
    def initBweight(self):
        self.totalBweight = 0
        self.totalBweightPerTrack = [0] * 4
        self.totalBweightPerHeight = [0] * MAX_BLDG_HEIGHT

        for hoodId in SUIT_HOOD_INFO:
            currHoodInfo = SUIT_HOOD_INFO[hoodId]
            
            if currHoodInfo.maxSuitBldgs == 0:
                continue
            
            weight = currHoodInfo.buildingWeight
            tracks = currHoodInfo.deptChances
            levels = currHoodInfo.levels

            heights = [0] * MAX_BLDG_HEIGHT
            for level in levels:
                minFloors, maxFloors = CogBuildingGlobalsAI.CogBuildingInfo[level-1].floors
                for i in range(minFloors -1, maxFloors):
                    heights[i] += 1
            
            currHoodInfo.buildingDifficulties = heights

            self.totalBweight += weight
            for i in range(len(tracks)):
                self.totalBweightPerTrack[i] = weight * tracks[i]
            for i in range(len(heights)):
                self.totalBweightPerHeight[i] = weight * heights[i]

    def initBuildingsAndPoints(self):
        self.buildingFrontDoors = {}
        self.buildingSideDoors = {}

        for point in self.frontDoorPoints:
            blockNumber = point.getLandmarkBuildingIndex()
            if point < 0:
                print(f'No landmark building for {repr(point)} in zone {self.zoneId}')
            elif blockNumber in self.buildingFrontDoors:
                print(f'Multiple front doors for building {blockNumber} in zone {self.zoneId}')
            else:
                self.buildingFrontDoors[blockNumber] = point

        for point in self.sideDoorPoints:
            blockNumber = point.getLandmarkBuildingIndex()
            if point < 0:
                print(f'No landmark building for {repr(point)} in zone {self.zoneId}')
            elif blockNumber in self.buildingSideDoors:
                self.buildingSideDoors[blockNumber].append(point)
            else:
                self.buildingSideDoors[blockNumber] = [point]

        """
        for blockNumber, bldg in self.hoodData.buildings.items():
            if bldg.isHQ():
                continue
            if blockNumber not in self.buildingFrontDoors:
                print(f'hot tubs')
            if blockNumber not in self.buildingSideDoors:
                print(f'hot tubs')
        """
            
            

    def getZoneId(self):
        return self.zoneId

    def genPath(self, startPoint, endPoint, minPathLen, maxPathLen):
        return self.dnaStore.getSuitPath(startPoint, endPoint, minPathLen, maxPathLen)

    def startup(self):
        self.upkeep()
        self.adjust()

    def createNewSuit(self, blockNumbers, streetPoints):
        random.shuffle(streetPoints)

        startPoint = None
        blockNumber = None
        dept = None

        while startPoint == None and len(blockNumbers) > 0:
            bn = random.choice(blockNumbers)
            blockNumbers.remove(bn)

            if bn in self.buildingSideDoors:
                for doorPoint in self.buildingSideDoors[bn]:
                    points = self.dnaStore.getAdjacentPoints(doorPoint)

                    i = points.getNumPoints() - 1
                    while blockNumber == None and i >= 0:
                        pi = points.getPointIndex(i)
                        p = self.pointIndexes[pi]
                        i -= 1

                        startTime = fromSuitBuilding
                        startTime += self.dnaStore.getSuitEdgeTravelTime(
                            doorPoint.getIndex(), pi,
                            self.suitWalkSpeed)

                        if not self.pointCollision(p, doorPoint, startTime):
                            startTime = fromSuitBuilding
                            startPoint = doorPoint
                            blockNumber = bn

        while startPoint is None and streetPoints:
            point = self.streetPoints[streetPoints.pop()]

            if not self.pointCollision(point, None, fromSky):
                startPoint = point

        if startPoint is None:
            print('start pt is none')
            return False

        suit = DistributedSuitAI(self.air, self)
        suit.startPoint = startPoint

        if blockNumber != None:
            suit.buildingSuit = 1
            # if suitTrack == None:
            dept = self.hoodData.buildings[blockNumber].getTrack()
        else:
            suit.flyInSuit = 1
            suit.attemptingTakeover = self.newSuitShouldAttemptTakeover()

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
        if not dept:
            department = pickFromFreqList(self.info.deptChances)
            dept = SuitDept(department).char
        else:
            department = suitDepts.index(dept)

        head = SuitHeads.at(department * 8 + tier)

        suit.dna = SuitDNA(suitType = 's', head = head, dept = dept)
        suit.actualLevel = level
        suit.initializePath()
        suit.generateWithRequired(suit.zoneId)
        suit.moveToNextLeg(None)
        self.suits.append(suit)
        if suit.buildingSuit:
            self.numBuildingSuits += 1
        if suit.flyInSuit:
            self.numFlyInSuits += 1

        if suit.attemptingTakeover:
            self.numAttemptingTakeover += 1

        return True

    def countNumNeededBuildings(self):
        return self.targetNumSuitBuildings - len(self.hoodData.suitBlocks)

    def newSuitShouldAttemptTakeover(self):
        numNeeded = self.countNumNeededBuildings()
        
        if self.numAttemptingTakeover >= numNeeded:
            return 0
        return 1

    def upkeep(self, task=None):
        desired = self.baseNumSuits + self.popAdjustment
        desired = min(desired, self.info.maxSuits - self.numBuildingSuits)
        deficit = (desired - self.numFlyInSuits + 3) // 4
        
        streetPoints = list(range(len(self.streetPoints)))
        
        while deficit > 0:
            if not self.createNewSuit([], streetPoints):
                break
            deficit -= 1

        suitBuildings = []
        for suitBlock in self.hoodData.suitBlocks:
            building = self.hoodData.buildings[suitBlock]
            if building.isSuitState():
                suitBuildings.append(suitBlock)
        targetBuildingNum = int(len(suitBuildings) * SUIT_BUILDING_NUM_SUITS)
        targetBuildingNum += deficit
        targetBuildingNum = min(targetBuildingNum, self.info.maxSuits - self.numFlyInSuits)
        buildingDeficit = (targetBuildingNum-self.numBuildingSuits + 3) // 4

        while buildingDeficit > 0:
            if not self.createNewSuit(suitBuildings, streetPoints):
                break
            buildingDeficit -= 1

        timeoutIndex = min(len(suitBuildings), len(SUIT_BUILDING_TIMEOUT) - 1)
        timeout = SUIT_BUILDING_TIMEOUT[timeoutIndex]
        if timeout != None:
            timeout *= 3600.0
            oldest = None
            oldestAge = 0
            now = time.time()
            for b in suitBuildings:
                building = self.hoodData.buildings[suitBlock]
                if hasattr(building, 'elevator'):
                    if building.elevator.getState() == 'WaitEmpty':
                        age = now - building.becameSuitTime
                        if age > oldestAge:
                            oldest = building
                            oldestAge = age

            if oldestAge > timeout:
                #oldest.b_setVictorList([0] * 4)
                #oldest.updateSavedBy(None)
                oldest.toonTakeOver()

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

    def suitTakeOver(self, blockNumber, dept, difficulty, buildingHeight):
        building = self.hoodData.buildings[blockNumber]
        building.suitTakeOver(dept, difficulty, buildingHeight)

    def recycleBuilding(self):
        bmin = self.info.minSuitBldgs
        current = len(self.hoodData.suitBlocks)

        if self.targetNumSuitBuildings > bmin and \
            current <= self.targetNumSuitBuildings:
            self.targetNumSuitBuildings -= 1
            self.assignSuitBuildings(1)

    def assignInitialSuitBuildings(self):
        totalBuildings = 0
        targetSuitBuildings = 0
        actualSuitBuildings = 0
        for sp in self.air.suitPlanners.values():
            totalBuildings += len(sp.frontDoorPoints)
            targetSuitBuildings += sp.targetNumSuitBuildings
            actualSuitBuildings += len(sp.hoodData.suitBlocks)
        wantedSuitBuildings = \
          int(totalBuildings * TOTAL_SUIT_BUILDING_PCT / 100)

        if actualSuitBuildings > 0:
            numReassigned = 0
                
            for sp in self.air.suitPlanners.values():
                numBuildings = len(sp.hoodData.suitBlocks)
                if numBuildings > sp.targetNumSuitBuildings:
                    more = numBuildings - sp.targetNumSuitBuildings
                    sp.targetNumSuitBuildings += more
                    targetSuitBuildings += more
                    numReassigned += more

        if wantedSuitBuildings > targetSuitBuildings:
            additionalBuildings = wantedSuitBuildings - targetSuitBuildings
            self.assignSuitBuildings(additionalBuildings)
                        
        elif wantedSuitBuildings < targetSuitBuildings:
            extraBuildings = targetSuitBuildings - wantedSuitBuildings
            self.unassignSuitBuildings(extraBuildings)

    def assignSuitBuildings(self, numToAssign):
        hoodInfo = SUIT_HOOD_INFO.copy()
        totalWeight = self.totalBweight
        totalWeightPerTrack = self.totalBweightPerTrack[:]
        totalWeightPerHeight = self.totalBweightPerTrack[:]

        numPerTrack = {'c': 0, 'l': 0, 'm': 0, 's':0}
        for sp in self.air.suitPlanners.values():
            sp.countNumBuildingsPerTrack(numPerTrack)
            numPerTrack['c'] += sp.pendingBuildingTracks.count('c')
            numPerTrack['l'] += sp.pendingBuildingTracks.count('l')
            numPerTrack['m'] += sp.pendingBuildingTracks.count('m')
            numPerTrack['s'] += sp.pendingBuildingTracks.count('s')

        numPerHeight = {0:0, 1: 0 , 2: 0, 3: 0, 4: 0,}
        for sp in self.air.suitPlanners.values():
            sp.countNumBuildingsPerHeight(numPerHeight)
            for i in range(len(numPerHeight)):
                numPerHeight[i] += sp.pendingBuildingHeights.count(i)

        while numToAssign > 0:
            smallestCount = None
            smallestTracks = []
            for trackIndex in range(4):
                if totalWeightPerTrack[trackIndex]:
                    track = SuitDNA.suitDepts[trackIndex]
                    count = numPerTrack[track]
                    if smallestCount == None or count < smallestCount:
                        smallestTracks = [track]
                        smallestCount = count
                    elif count == smallestCount:
                        smallestTracks.append(track)

            if not smallestTracks:
                return

            buildingTrack = random.choice(smallestTracks)
            buildingTrackIndex = SuitDNA.suitDepts.index(buildingTrack)

            smallestCount = None
            smallestHeights = []
            for height in range(MAX_BLDG_HEIGHT):
                if totalWeightPerHeight[height]:
                    count = float(numPerHeight[height]) / float(BUILDING_HEIGHT_DISTRIBUTION[height])
                    if smallestCount == None or count < smallestCount:
                        smallestHeights = [height]
                        smallestCount = count
                    elif count == smallestCount:
                        smallestHeights.append(height)

            if not smallestHeights:
                return

            buildingHeight = random.choice(smallestHeights)
            
            repeat = 1
            while repeat and buildingTrack != None and buildingHeight != None:
                if len(hoodInfo) == 0:
                    return
                    
                repeat = 0
                
                currHoodInfo = self.chooseStreetWithPreference(hoodInfo, buildingTrackIndex, buildingHeight)

                zoneId = currHoodInfo.zoneId

                if zoneId in self.air.suitPlanners:
                    sp = self.air.suitPlanners[zoneId]
                
                    numTarget = sp.targetNumSuitBuildings
                    numTotalBuildings = len(sp.frontDoorPoints)
                else:
                    numTarget = 0
                    numTotalBuildings = 0
                
                if numTarget >= currHoodInfo.maxSuitBldgs or \
                   numTarget >= numTotalBuildings:
                    del hoodInfo[zoneId]
                    weight = currHoodInfo.buildingWeight
                    tracks = currHoodInfo.deptChances
                    heights = currHoodInfo.buildingDifficulties
                    totalWeight -= weight

                    for track in totalWeightPerTrack:
                        totalWeightPerTrack[track] -= weight * tracks[track]
                    for height in totalWeightPerHeight:
                        totalWeightPerHeight[height] -= weight * heights[height]

                    if totalWeightPerTrack[buildingTrackIndex] <= 0:
                        buildingTrack = None

                    if totalWeightPerHeight[buildingHeight] <= 0:
                        buildingHeight = None
                    
                    repeat = 1

            if buildingTrack != None and buildingHeight != None:
                sp.targetNumSuitBuildings += 1
                sp.pendingBuildingTracks.append(buildingTrack)
                sp.pendingBuildingHeights.append(buildingHeight)
                numPerTrack[buildingTrack] += 1
                numPerHeight[buildingHeight] += 1
                numToAssign -= 1

    def unassignSuitBuildings(self, numToAssign):
        hoodInfo = SUIT_HOOD_INFO.copy()
        totalWeight = self.totalBweight

        while numToAssign > 0:
            repeat = 1
            while repeat:
                if len(hoodInfo) == 0:
                    return
                    
                repeat = 0
                currHoodInfo = self.chooseStreetNoPreference(hoodInfo, totalWeight)

                zoneId = currHoodInfo.zoneId

                if zoneId in self.air.suitPlanners:
                    sp = self.air.suitPlanners[zoneId]
                
                    numTarget = sp.targetNumSuitBuildings
                    numTotalBuildings = len(sp.frontDoorPoints)
                else:
                    numTarget = 0
                    numTotalBuildings = 0
                
                if numTarget <= currHoodInfo.minSuitBldgs:
                    del hoodInfo[zoneId]
                    totalWeight -= currHoodInfo.buildingWeight
                    repeat = 1

            sp.targetNumSuitBuildings -= 1
            numToAssign -= 1

    def chooseStreetNoPreference(self, hoodInfo, totalWeight):
        c = random.random() * totalWeight

        t = 0
        for i in hoodInfo:
            currHoodInfo = hoodInfo[i]
            weight = currHoodInfo.buildingWeight
            t += weight
            if c < t:
                return currHoodInfo

        return random.choice(hoodInfo)

    def chooseStreetWithPreference(self, hoodInfo, buildingTrackIndex,
                                   buildingHeight):
        dist = []
        for i in hoodInfo:
            currHoodInfo = hoodInfo[i]
            weight = currHoodInfo.buildingWeight
            thisValue = weight * currHoodInfo.deptChances[buildingTrackIndex] * currHoodInfo.buildingDifficulties[buildingHeight]
            dist.append(thisValue)
            
        totalWeight = sum(dist)
        
        c = random.random() * totalWeight

        t = 0
        for i in range(len(hoodInfo)):
            t += dist[i]
            if c < t:
                return hoodInfo[i]

        return random.choice(hoodInfo)

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
        possiblePoints = []
        backup = []

        if suit.attemptingTakeover:
            for blockNumber in self.hoodData.toonBlocks:
                bldg = self.hoodData.buildings[blockNumber]

                if not NPCToons.isZoneProtected(bldg.interiorZoneId):
                    if blockNumber in self.buildingFrontDoors:
                        possiblePoints.append((blockNumber, self.buildingFrontDoors[blockNumber]))

        for point in self.streetPoints:
            backup.append((None, point))

        if not possiblePoints:
            possiblePoints = backup
            backup = []
            if suit.attemptingTakeover:
                suit.attemptingTakeover = False
                self.numAttemptingTakeover -= 1
            
        if suit.attemptingTakeover:
            minPathLen = MIN_TAKEOVER_PATH_LEN
        else:
            minPathLen = MIN_PATH_LEN

        retries = 0
        
        while len(possiblePoints) > 0 and retries < 50:
            point = random.choice(possiblePoints)
            possiblePoints.remove(point)
            
            if not possiblePoints:
                possiblePoints = backup
                backup = []

            path = self.genPath(suit.startPoint, point[1], minPathLen, MAX_PATH_LEN)

            if path and not self.pathCollision(path, startTime):
                suit.endPoint = point[1]
                suit.minPathLen = minPathLen
                suit.maxPathLen = MAX_PATH_LEN
                suit.buildingDestination = point[0]
                # print('CHOSEN PATH:', suit.startPoint, endPoint, path)
                suit.path = path
                return 1

            retries += 1

    def removeSuit(self, suit: DistributedSuitAI):
        suit.requestDelete()
        self.suits.remove(suit)
        if suit.buildingSuit:
           self.numBuildingSuits -= 1
        if suit.flyInSuit:
            self.numFlyInSuits -= 1
        if suit.attemptingTakeover:
            self.numAttemptingTakeover -= 1

    def requestBattle(self, zoneId, suit: DistributedSuitAI, toonId) -> bool:
        pos = self.zone2battlePos[zoneId]

        battle = self.battleMgr.newBattle(suit, toonId, zoneId, zoneId, pos)
        return True

    def __battleFinished(self):
        pass

    def __suitCanJoinBattle(self, zoneId):
        battle = self.battleMgr.getBattle(zoneId)
        if len(battle.suits) >= self.info.maxBattleSuits:
            return 0
        jChanceList = self.info.joinChances
        ratioIdX = len(battle.toons) - battle.numSuitsEver + 2
        if ratioIdX >= 0:
            if ratioIdX < len(jChanceList):
                if random.randint(0, 99) < jChanceList[ratioIdX]:
                    return 1
            else:
                return 1
        return 0

    def checkForBattle(self, zoneId, suit):
        if self.battleMgr.cellHasBattle(zoneId):
            if self.__suitCanJoinBattle(zoneId) and \
               self.battleMgr.requestBattleAddSuit(zoneId, suit):
                pass
            else:
                suit.flyAwayNow()
            return 1
        return 0

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

    def getBattle(self, zoneId):
        return self.cell2Battle.get(zoneId)

    def removeBattle(self, battle):
        cellId = battle.battleCellId

        if cellId in self.cell2Battle:
            battle.requestDelete()
            del self.cell2Battle[cellId]

    def requestBattleAddSuit(self, cellId, suit):
        return self.cell2Battle[cellId].suitRequestJoin(suit)

    def cellHasBattle(self, cellId):
        return cellId in self.cell2Battle