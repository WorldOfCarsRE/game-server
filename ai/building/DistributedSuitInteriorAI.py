from ai.DistributedObjectAI import DistributedObjectAI

# from ai.battle import DistributedBattleBldgAI

from ai.ToonBarrier import ToonBarrier

from direct.fsm.FSM import FSM
from typing import Optional

# This allows plenty of time for clients to load building assets.
# Adjust if needed.
JOIN_TIMEOUT = 30
ELEVATOR_JOIN_TIMEOUT = 8
RESERVES_JOIN_TIMEOUT = 7

class DistributedSuitInteriorAI(DistributedObjectAI, FSM):
    defaultTransitions = {
            'WaitForAllToonsInside': ['Elevator'],
            'Elevator': ['Battle'],
            'Battle': ['ReservesJoining, BattleDone'],
            'ReservesJoining': ['Battle'],
            'BattleDone': ['Resting', 'Reward'],
            'Resting': ['Elevator'],
            'Reward': ['Off'],
            'Off': ['WaitForAllToonsInside'],
        }

    def __init__(self, air, elevator):
        DistributedObjectAI.__init__(self, air)
        FSM.__init__(self, self.__class__.__name__)

        self.extZoneId = elevator.bldg.exteriorZoneId
        self.zoneId = elevator.bldg.zoneId
        self.numFloors = elevator.bldg.numFloors

        self._barrier: Optional[ToonBarrier] = None

        self.toons = []
        self.toonIds = elevator.seats[:]
        for toonId in self.toonIds:
            if toonId != None:
                self.addToon(toonId)

        self.savedByMap = {}

        self.bldg = elevator.bldg

        self.demand('WaitForAllToonsInside')

    def delete(self):
        self.ignoreAll()

        DistributedObjectAI.delete(self)

    def handleUnexpectedExit(self, toonId):
        self.removeToon(toonId)
        if len(self.toons) == 0:
            if self.state == 'Resting':
                pass
            elif self.battle == None:
                self.bldg.deleteSuitInterior() #

    def addToon(self, toonId):
        if toonId not in self.air.doTable:
            return

        event = self.air.getDeleteDoIdEvent()
        self.avatarExitEvents.append(event)
        self.accept(event, self.handleUnexpectedExit, extraArgs=[toonId])

        self.toons.append(toonId)

    def removeToon(self, toonId):
        if self.toons.count(toonId):
            self.toons.remove(toonId)
        if self.toonIds.count(toonId):
            self.toonIds[self.toonIds.index(toonId)] = None

        if self._barrier is not None and self._barrier.active:
            self._barrier.clear(toonId)

        event = self.air.getDeleteDoIdEvent(toonId)
        if event in self.avatarExitEvents:
            self.avatarExitEvents.remove(event)
        self.ignore(event)

    def getZoneId(self):
        return self.zoneId

    def getExtZoneId(self):
        return self.extZoneId

    def getDistBldgDoId(self):
        return self.bldg.doId

    def getNumFloors(self):
        return self.numFloors

    def d_setToons(self):
        self.sendUpdate('setToons', self.getToons())

    def getToons(self):
        toonIds = []
        for toonId in self.toonIds:
            if toonId == None:
                toonIds.append(0)
            else:
                toonIds.append(toonId)

        return [toonIds, 0]
       
    def d_setSuits(self):
        pass

    def getSuits(self):
        pass

    def getState(self):
        state = self.state[0].lower() + self.state[1:]
        return [state, globalClockDelta.getRealNetworkTime()]

    def d_setState(self, state):
        state = self.state[0].lower() + self.state[1:]
        self.sendUpdate('setState', [state, globalClockDelta.getRealNetworkTime()])

    def b_setState(self, state):
        self.request(state)
        self.d_setState(state)

    def setAvatarJoined(self):
        avId = self.air.currentAvatarSender
        if self.toons.count(avId) == 0:
            return

        toon = self.air.doTable.get(avId)
        if toon != None:
            self.savedByMap[avId] = (avatar.getName(), avatar.dna.asTuple())

        if self._barrier is not None and self._barrier.active:
            self._barrier.clear(avId)
        
    def elevatorDone(self):
        avId = self.air.currentAvatarSender
        if self.toons.count(avId) == 0:
            return
        if self.state != 'Elevator':
            return
        if self._barrier is not None and self._barrier.active:
            self._barrier.clear(senderId)
       
    def reserveJoinDone(self):
        avId = self.air.currentAvatarSender
        if self.toons.count(avId) == 0:
            return
        if self.state != 'ReservesJoining':
            return
        if self._barrier is not None and self._barrier.active:
            self._barrier.clear(senderId)

    def enterWaitForAllToonsInside(self):
        self._barrier = ToonBarrier(self.uniqueName('wait-all-toons'), self.toons, JOIN_TIMEOUT, self._waitForAllToonsDone)

    def _waitForAllToonsDone(self):
        self.b_setState('Elevator')

    def exitWaitForAllToonsInside(self):
        pass

    def enterElevator(self):
        self._barrier = ToonBarrier(self.uniqueName('enter-elevator'), self.toons, ELEVATOR_JOIN_TIMEOUT, self._serverElevatorDone)

    def _serverElevatorDone(self):
        self.b_setState('Battle')

    def exitElevator(self):
        pass

    def enterBattle(self):
        pass

    def exitBattle(self):
        pass

    def enterReservesJoining(self):
        self._barrier = ToonBarrier(self.uniqueName('enter-reserves-joining'), self.toons, RESERVES_JOIN_TIMEOUT, self._serverReservesDone)

    def _serverReservesDone(self):
        self.b_setState('Battle')

    def exitReservesJoining(self):
        pass

    def enterBattleDone(self):
        pass

    def exitBattleDone(self):
        pass

    def enterResting(self):
        pass

    def exitResting(self):
        pass

    def enterReward(self):
        victors = self.toonIds[:]

        savedBy = []
        for v in victors:
            tuple = self.savedByMap.get(v)
            if tuple:
                savedBy.append([v, tuple[0], tuple[1])

        self.bldg.request('WaitForVictors', [victors, savedBy])

        self.d_setState('Reward')

    def exitReward(self):
        pass

    def enterOff(self):
        pass

    def exitOff(self):
        pass
