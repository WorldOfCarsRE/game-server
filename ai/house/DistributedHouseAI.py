from ai.DistributedObjectAI import DistributedObjectAI

class DistributedHouseAI(DistributedObjectAI):

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.housePos = 0
        self.houseType = 0
        self.gardenPos = 0
        self.avId = 0
        self.name = ''
        self.color = 0
        self.atticItems = ''
        self.interiorItems = ''
        self.atticWallpaper = ''
        self.interiorWallpaper = ''
        self.atticWindows = ''
        self.interiorWindows = ''
        self.deletedItems = ''
        self.cannonEnabled = 0

    def announceGenerate(self):
        self.sendUpdate('setHouseReady', [])

    def getHousePos(self) -> int:
        return self.housePos

    def getHouseType(self) -> int:
        return self.houseType

    def getGardenPos(self) -> int:
        return self.gardenPos

    def getAvatarId(self) -> int:
        return self.avId

    def getName(self) -> str:
        return self.name

    def getColor(self) -> int:
        return self.color

    def getAtticItems(self):
        return self.atticItems

    def getInteriorItems(self):
        return self.interiorItems

    def getAtticWallpaper(self):
        return self.atticWallpaper

    def getInteriorWallpaper(self):
        return self.interiorWallpaper

    def getAtticWindows(self):
        return self.atticWindows

    def getInteriorWindows(self):
        return self.interiorWindows

    def getDeletedItems(self):
        return self.deletedItems

    def getCannonEnabled(self) -> int:
        return self.cannonEnabled