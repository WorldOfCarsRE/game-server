from panda3d.core import Point3, Vec3

from ai.DistributedObjectAI import DistributedObjectAI

from dataclasses import dataclass
from dataslots import with_slots

from direct.task.Task import Task
import random

from typing import Optional

from .SuitGlobals import *
from .SuitTimings import victoryDance, fromSky, toSky, fromSuitBuilding, toSuitBuilding, toToonBuilding

@with_slots
@dataclass
class SuitDNA:
    suitType: str = 's'
    head: SuitHeads = SuitHeads.FLUNKY
    dept: str = 'c'

    def makeNetString(self) -> bytes:
        if self.suitType == 's':
            return ''.join((self.suitType, self.head.value.ljust(3, '\x00'), self.dept)).encode('ascii')
        elif self.suitType == 'b':
            return ''.join((self.suitType, self.dept)).encode('ascii')
        else:
            raise ValueError(f'Unknown suit dna type: {self.suitType}')

class DistributedSuitBaseAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.dna = SuitDNA()
        self._level = 1
        self.skelecog = False
        self.revives = 0
        self.revivedFlag = 0
        self.hp = 6
        self.maxHP = 6

    def getDNAString(self):
        return self.dna.makeNetString()

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level):
        self._level = level
        self.hp = SuitAttributes[self.head].hps[self.level]
        self.maxHP = self.hp

    @property
    def actualLevel(self) -> int:
        return getActualFromRelativeLevel(self.head, self.level) + 1

    @actualLevel.setter
    def actualLevel(self, actualLevel):
        relativeLevel = (actualLevel - SuitAttributes[self.head].level) - 1
        self.level = relativeLevel

    @property
    def head(self) -> SuitHeads:
        return self.dna.head

    def getLevelDist(self):
        return self.level

    def getSkelecog(self):
        return self.skelecog

    def getSkeleRevives(self):
        return self.revives

    def getHP(self):
        return self.hp

    def d_setHP(self):
        self.sendUpdate('setHP', [self.hp])

    def b_setHP(self, hp):
        self.hp = hp
        self.d_setHP()

    def d_setBrushOff(self, index):
        self.sendUpdate('setBrushOff', [index])

    def reviveCheckAndClear(self):
        if self.revivedFlag:
            self.revivedFlag = False
            return True
        return False

    @property
    def attributes(self) -> SuitAttribute:
        return SuitAttributes[self.head]

    def pickSuitAttack(self) -> Optional[int]:
        rng = random.randint(0, 99)

        attacks = self.attributes.attacks

        for i, attack in enumerate(attacks):
            print(f'{self.level}: {rng} < {attack.frequencies[self.level]}')
            if rng < attack.frequencies[self.level]:
                return i
        else:
            return i

    def testSuitAttackHit(self, attackIndex):
        attack: SuitAttackInfo = self.attributes.attacks[attackIndex]
        acc = attack.accuracies[self.level]
        if random.randint(0, 99) < acc:
            return attack.damages[self.level]
        else:
            return 0

    def getDeathEvent(self):
        return 'cogDead-%s' % self.doId

    def resume(self):
        if self.hp <= 0:
            messenger.send(self.getDeathEvent())
            self.requestDelete()

    def prepareToJoinBattle(self):
        pass

from panda3d.toontown import SuitLegList, DNASuitPoint, SuitLeg
from typing import Optional, List

class PathState(IntEnum):
    STOP = 0
    MOVE = 1
    STOP_FLYAWAY = 2
    UNKNOWN = 3
    VICTORY_FLYAWAY = 4

UPDATE_TIMESTAMP_INTERVAL = 60.0

class DistributedSuitAI(DistributedSuitBaseAI):
    def __init__(self, air, suitPlanner):
        DistributedSuitBaseAI.__init__(self, air)
        self.suitPlanner = suitPlanner

        self.pathState = 0
        self.pathPositionIndex = 0
        self.pathPositionTimestamp = 0
        self.pathStartTime = 0
        self.startPoint: Optional[DNASuitPoint] = None
        self.endPoint: Optional[DNASuitPoint] = None
        self.legList: Optional[SuitLegList] = None
        self.path: Optional[List[int]] = None
        self.currentLeg = 0
        self.legType = 0

        self.confrontPos = Point3()
        self.confrontHpr = Vec3()

    def getSPDoId(self):
        if self.suitPlanner:
            return self.suitPlanner.doId
        else:
            return 0

    def getPathEndpoints(self):
        from ai.suit.DistributedSuitPlannerAI import MIN_PATH_LEN, MAX_PATH_LEN

        return self.startPoint.getIndex(), self.endPoint.getIndex(), \
               MIN_PATH_LEN, MAX_PATH_LEN

    def getPathState(self):
        return self.pathState

    def b_setPathPosition(self, pathPositionIndex, ts):
        self.pathPositionIndex = pathPositionIndex
        self.pathPositionTimestamp = ts
        self.sendUpdate('setPathPosition', self.getPathPosition())

    def getPathPosition(self):
        return self.pathPositionIndex, globalClockDelta.localToNetworkTime(self.pathPositionTimestamp)

    def requestBattle(self, x, y, z, h, p, r):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)
        if not av:
            return

        print('requestBattle', x, y, z, h, p, r)

        if self.pathState != PathState.MOVE:
            if self.pathState == PathState.STOP_FLYAWAY or self.pathState == PathState.VICTORY_FLYAWAY:
                self.sendUpdate('setBrushOff', [0])
            self.sendUpdateToAvatar(avId, 'denyBattle', [])
            return

        if self.legType != SuitLeg.TWalk:
            self.sendUpdate('setBrushOff', [0])
            self.sendUpdateToAvatar(avId, 'denyBattle', [])
            return

        self.confrontPos = Point3(x, y, z)
        self.confrontHpr = Vec3(h, p, r)

        if not self.suitPlanner.requestBattle(self.zoneId, self, avId):
            self.sendUpdate('setBrushOff', [0])
            self.sendUpdateToAvatar(avId, 'denyBattle', [])
            return

    def pointInMyPath(self, point, elapsed, collisionBuffer=5):
        if self.pathState != PathState.MOVE:
            return 0
        if not self.suitPlanner:
            return
        then = globalClock.getFrameTime() + elapsed
        elapsed = then - self.pathStartTime
        return self.legList.isPointInRange(point, elapsed - collisionBuffer, elapsed + collisionBuffer)

    def initializePath(self):
        self.legList = SuitLegList(self.path,
                                   self.suitPlanner.dnaStore,
                                   self.suitPlanner.suitWalkSpeed,
                                   fromSky,
                                   toSky,
                                   fromSuitBuilding,
                                   toSuitBuilding,
                                   toToonBuilding)
        self.pathStartTime = globalClock.getFrameTime()
        self.pathPositionIndex = 0
        self.pathState = PathState.MOVE
        self.currentLeg = 0
        self.zoneId = self.legList.getZoneId(0)
        self.legType = self.legList.getType(0)

    def resync(self):
        self.b_setPathPosition(self.currentLeg, self.pathStartTime + self.legList.getStartTime(self.currentLeg))

    def moveToNextLeg(self, task=None):
        now = globalClock.getFrameTime()
        elapsed = now - self.pathStartTime
        nextLeg = self.legList.getLegIndexAtTime(elapsed, self.currentLeg)
        numLegs = self.legList.getNumLegs()
        if self.currentLeg != nextLeg:
            self.currentLeg = nextLeg
            self.__beginLegType(self.legList.getType(nextLeg))
            zoneId = self.legList.getZoneId(nextLeg)
            self.__enterZone(zoneId)
            if 1:
                leg = self.legList[nextLeg]
                pos = leg.getPosAtTime(elapsed - leg.getStartTime())
                self.sendUpdate('debugSuitPosition', [elapsed, nextLeg, pos[0], pos[1], globalClockDelta.localToNetworkTime(now)])
        if now - self.pathPositionTimestamp > UPDATE_TIMESTAMP_INTERVAL:
            self.resync()
        if self.pathState != PathState.MOVE:
            return Task.done
        nextLeg += 1
        while nextLeg + 1 < numLegs and self.legList.getZoneId(nextLeg) == self.zoneId and self.legList.getType(nextLeg) == self.legType:
            nextLeg += 1

        if nextLeg < numLegs:
            nextTime = self.legList.getStartTime(nextLeg)
            delay = nextTime - elapsed
            taskMgr.doMethodLater(delay, self.moveToNextLeg, self.uniqueName('move'))
        else:
            # if self.attemptingTakeover:
            #     self.startTakeOver()
            self.requestRemoval()
        return Task.done

    def requestRemoval(self):
        if self.suitPlanner is not None:
            self.suitPlanner.removeSuit(self)
        else:
            self.requestDelete()

    def __beginLegType(self, legType):
        self.legType = legType
        if legType == SuitLeg.TToCoghq:
            self.openCogHQDoor(1)
        elif legType == SuitLeg.TFromCoghq:
            self.openCogHQDoor(0)

    def __enterZone(self, zoneId):
        if zoneId != self.zoneId:
            # print('suit zone change', self.zoneId, '->', zoneId)
            #self.suitPlanner.zoneChange(self, self.zoneId, zoneId)
            self.sendSetZone(zoneId)
            self.zoneId = zoneId
            # if self.pathState == 1:
            #     self.suitPlanner.checkForBattle(zoneId, self)

    def resume(self):
        if self.hp <= 0:
            self.requestRemoval()
        else:
            self.danceNowFlyAwayLater()

    def openCogHQDoor(self, enter):
        blockNumber = int(self.legList.get_block_number(self.currentLeg))
        try:
            door = self.suitPlanner.cogHQDoors[blockNumber]
        except:
            return

        if enter:
            door.d_suitEnter(self.doId)
        else:
            door.d_suitExit(self.doId)

    def stopPathNow(self):
        taskMgr.remove(self.uniqueName('move'))

    def flyAwayNow(self):
        self.b_setPathState(PathState.STOP_FLYAWAY)
        self.stopPathNow()
        name = self.uniqueName('flyAwayNow')
        taskMgr.remove(name)
        taskMgr.doMethodLater(TO_SKY, self.finishFlyAwayNow, name)

    def danceNowFlyAwayLater(self):
        self.b_setPathState(PathState.VICTORY_FLYAWAY)
        self.stopPathNow()
        name = self.uniqueName('danceNowFlyAwayLater')
        taskMgr.remove(name)
        taskMgr.doMethodLater(VICTORY_DANCE + TO_SKY, self.finishFlyAwayNow, name)

    def finishFlyAwayNow(self, task):
        self.requestRemoval()
        return Task.done

    def prepareToJoinBattle(self):
        self.b_setPathState(PathState.STOP)

    def b_setPathState(self, pathState):
        self.pathState = pathState
        self.sendUpdate('setPathState', [self.pathState])