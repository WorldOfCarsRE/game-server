from ai.DistributedObjectAI import DistributedObjectAI
from ai.catalog.CatalogItemList import CatalogItemList
from ai.catalog import CatalogItem

class DistributedHouseInteriorAI(DistributedObjectAI):

    def __init__(self, air, house):
        DistributedObjectAI.__init__(self, air)
        self.house = house
        self.houseId = 0
        self.houseIndex = 0
        self.wallpaper = self.house.interiorWallpaper
        self.windows = self.house.interiorWindows

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
        self.wallpaper = CatalogItemList(wallpaper, store = CatalogItem.Customization)

    def d_setWallpaper(self, items):
        self.sendUpdate('setWallpaper', [items.getBlob(store = CatalogItem.Customization)])

    def b_setWallpaper(self, wallpaper):
        self.setWallpaper(wallpaper)

        if self.generated:
            self.d_setWallpaper(wallpaper)

    def getWallpaper(self) -> str:
        return self.wallpaper.getBlob(store = CatalogItem.Customization)

    def setWindows(self, windows):
        self.windows = CatalogItemList(windows, store = CatalogItem.Customization | CatalogItem.WindowPlacement)

    def d_setWindows(self, windows):
        self.sendUpdate('setWindows', [windows.getBlob(store = CatalogItem.Customization | CatalogItem.WindowPlacement)])

    def b_setWindows(self, windows):
        self.setWindows(windows)

        if self.generated:
            self.d_setWindows(windows)

    def getWindows(self) -> str:
        return self.windows.getBlob(store = CatalogItem.Customization | CatalogItem.WindowPlacement)