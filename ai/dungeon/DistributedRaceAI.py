from .DistributedDungeonAI import DistributedDungeonAI

class DistributedRaceAI(DistributedDungeonAI):
    def __init__(self, air):
        DistributedDungeonAI.__init__(self, air)
