from direct.distributed.DistributedObjectAI import DistributedObjectAI

class DistributedZoneAI(DistributedObjectAI):
    def __init__(self, air, name, mapId):
        DistributedObjectAI.__init__(self, air)
        self.name = name
        self.mapId = mapId
        self.catalogItemId = mapId
        self.interactiveObjects = []
        self.playersInZone = []
        self.mute = 0

    def getName(self):
        return self.name

    def getMapId(self):
        return self.mapId

    def getCatalogItemId(self):
        return self.catalogItemId

    def getInteractiveObjectCount(self):
        return len(self.interactiveObjects)

    def updateObjectCount(self):
        self.sendUpdate('setInteractiveObjectCount', [self.getInteractiveObjectCount()])

    def getPlayerCount(self):
        return len(self.playersInZone)

    def getMute(self):
        return self.mute
