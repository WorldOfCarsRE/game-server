from direct.fsm.ClassicFSM import ClassicFSM
from direct.fsm.State import State
from ai.DistributedObjectAI import DistributedObjectAI

class DistributedAnimatedPropAI(DistributedObjectAI):

    def __init__(self, air, propId):
        DistributedObjectAI.__init__(self, air)

        self.fsm = ClassicFSM('DistributedAnimatedPropAI', [
            State('off', self.enterOff, self.exitOff, ['playing']),
            State('attract', self.enterAttract, self.exitAttract, ['playing']),
            State('playing', self.enterPlaying, self.exitPlaying, ['attract'])], 'off', 'off')

        self.fsm.enterInitialState()

        self.propId = propId
        self.avatarId = 0

    def delete(self):
        self.fsm.requestFinalState()
        del self.fsm

        DistributedObjectAI.delete(self)

    def getPropId(self):
        return self.propId

    def getAvatarInteract(self):
        return self.avatarId

    def getInitialState(self):
        return [self.fsm.getCurrentState().getName(), globalClockDelta.getRealNetworkTime()]

    def getOwnerDoId(self):
        return self.ownerDoId

    def requestInteract(self):
        avatarId = self.air.currentAvatarSender
        stateName = self.fsm.getCurrentState().getName()

        if stateName != 'playing':
            self.sendUpdate('setAvatarInteract', [avatarId])
            self.avatarId = avatarId
            self.fsm.request('playing')
        else:
            self.sendUpdateToAvatar(avatarId, 'rejectInteract', [])

    def requestExit(self):
        avatarId = self.air.currentAvatarSender

        if avatarId == self.avatarId:
            stateName = self.fsm.getCurrentState().getName()

            if stateName == 'playing':
                self.sendUpdate('avatarExit', [avatarId])
                self.fsm.request('attract')

    def getState(self):
        return [self.fsm.getCurrentState().getName(), globalClockDelta.getRealNetworkTime()]

    def d_setState(self, state):
        self.sendUpdate('setState', [state, globalClockDelta.getRealNetworkTime()])

    def enterOff(self):
        pass

    def exitOff(self):
        pass

    def enterAttract(self):
        self.d_setState('attract')

    def exitAttract(self):
        pass

    def enterPlaying(self):
        self.d_setState('playing')

    def exitPlaying(self):
        pass