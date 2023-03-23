from ai.DistributedObjectAI import DistributedObjectAI

class DistributedLobbyAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.dungeonItemId = 0
        self.hotSpotName = ''

    def getDungeonItemId(self):
        return self.dungeonItemId

    def getHotSpotName(self):
        return self.hotSpotName
