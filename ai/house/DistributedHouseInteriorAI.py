from ai.DistributedObjectAI import DistributedObjectAI

class DistributedHouseInteriorAI(DistributedObjectAI):

    def __init__(self, air, house):
        DistributedObjectAI.__init__(self, air)
        self.house = house
        self.houseId = 0
        self.houseIndex = 0
        self.wallpaper = ''
        self.windows = ''

    def setHouseId(self, houseId):
        self.houseId = houseId

    def d_setHouseId(self, houseId):
        self.sendUpdate('setHouseId', [houseId])

    def b_setHouseId(self, houseId):
        self.setHouseId(houseId)
        self.d_setHouseId(houseId)

    def getHouseId(self) -> int:
        return self.houseId

    def setHouseIndex(self, houseIndex):
        self.houseIndex = houseIndex

    def d_setHouseIndex(self, houseIndex):
        self.sendUpdate('setHouseIndex', [houseIndex])

    def b_setHouseIndex(self, houseIndex):
        self.setHouseIndex(houseIndex)
        self.d_setHouseIndex(houseIndex)

    def getHouseIndex(self) -> int:
        return self.houseIndex

    def setWallpaper(self, wallpaper):
        self.wallpaper = wallpaper

    def d_setWallpaper(self, wallpaper):
        self.sendUpdate('setWallpaper', [wallpaper])

    def b_setWallpaper(self, wallpaper):
        self.setWallpaper(wallpaper)

        if self.generated:
            self.d_setWallpaper(wallpaper)

    def getWallpaper(self) -> str:
        return self.wallpaper

    def setWindows(self, windows):
        self.windows = windows

    def d_setWindows(self, windows):
        self.sendUpdate('setWindows', [windows])

    def b_setWindows(self, windows):
        self.setWindows(windows)

        if self.generated:
            self.d_setWindows(windows)

    def getWindows(self) -> str:
        return self.windows