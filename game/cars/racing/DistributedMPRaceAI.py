from direct.directnotify.DirectNotifyGlobal import directNotify

from .DistributedRaceAI import DistributedRaceAI

class DistributedMPRaceAI(DistributedRaceAI):
    notify = directNotify.newCategory("DistributedMPRaceAI")

    def __init__(self, air, track):
        DistributedRaceAI.__init__(self, air, track)

    def getWaitForObjects(self):
        return self.playerIds
