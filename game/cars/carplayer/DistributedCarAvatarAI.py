from direct.distributed.DistributedObjectAI import DistributedObjectAI

class DistributedCarAvatarAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.state: int = 1

    def d_setTelemetry(self, x: int, y: int, unk0: int, unk1: int, unk2: int, angle: int, unk3, timeStamp: int):
        self.sendUpdate('setTelemetry', [x, y, unk0, unk1, unk2, angle, unk3, timeStamp])

    def setState(self, state: int):
        self.state = state
        self.d_setState(state)

    def d_setState(self, state: int):
        self.sendUpdate('setState', [state])

    def getState(self) -> int:
        return self.state
