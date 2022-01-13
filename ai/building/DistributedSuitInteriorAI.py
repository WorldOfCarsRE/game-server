from ai.DistributedObjectAI import DistributedObjectAI

# from ai.battle import DistributedBattleBldgAI

from direct.fsm.FSM import FSM

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

        self.bldg = elevator.bldg

        self.demand('WaitForAllToonsInside')

    def delete(self):
        self.ignoreAll()

        DistributedObjectAI.delete(self)

    def getZoneId(self):
        return self.zoneId

    def getExtZoneId(self):
        return self.extZoneId

    def getDistBldgDoId(self):
        return self.bldg.doId

    def getNumFloors(self):
        return self.numFloors

    def d_setToons(self):
        pass

    def getToons(self):
        pass
        
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
        
    def elevatorDone(self):
        avId = self.air.currentAvatarSender
        
    def reserveJoinDone(self):
        avId = self.air.currentAvatarSender

    def enterWaitForAllToonsInside(self):
        pass

    def exitWaitForAllToonsInside(self):
        pass

    def enterElevator(self):
        pass

    def exitElevator(self):
        pass

    def enterBattle(self):
        pass

    def exitBattle(self):
        pass

    def enterReservesJoining(self):
        pass

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
        pass

    def exitReward(self):
        pass

    def enterOff(self):
        pass

    def exitOff(self):
        pass
