from .DistributedRaceAI import DistributedRaceAI

class DistributedSPRaceAI(DistributedRaceAI):

    def __init__(self, air, track):
        DistributedRaceAI.__init__(self, air, track)
