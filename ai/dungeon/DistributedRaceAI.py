from .DistributedDungeonAI import DistributedDungeonAI

class DistributedRaceAI(DistributedDungeonAI):
    COUNTDOWN_TIME = 3

    def __init__(self, air):
        DistributedDungeonAI.__init__(self, air)

    def syncReady(self):
        self.sendUpdate('setCountDown', [self.COUNTDOWN_TIME])
