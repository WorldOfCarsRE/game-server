from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.DistributedObjectUD import DistributedObjectUD

class DistributedLobbyUD(DistributedObjectUD):
    notify = directNotify.newCategory("DistributedLobbyUD")

    def __init__(self, air):
        DistributedObjectUD.__init__(self, air)
        self.dungeonItemId: int = 0
        self.hotSpotName: str = ''

        self.contexts: list = []

    def getDungeonItemId(self):
        return self.dungeonItemId

    def getHotSpotName(self):
        return self.hotSpotName
