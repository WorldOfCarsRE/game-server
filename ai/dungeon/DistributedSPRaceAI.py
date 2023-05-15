from .DistributedRaceAI import DistributedRaceAI

class DistributedSPRaceAI(DistributedRaceAI):

    def __init__(self, air):
        DistributedRaceAI.__init__(self, air)
