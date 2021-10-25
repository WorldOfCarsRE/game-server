from ai.DistributedObjectAI import DistributedObjectAI
from ai.catalog.CatalogItemList import CatalogItemList
from ai.catalog import CatalogItem

class DistributedFurnitureManagerAI(DistributedObjectAI):

    def __init__(self, air, house, isInterior):
        DistributedObjectAI.__init__(self, air)

        self.house = house
        self.isInterior = isInterior
        self.director = 0
        self.items = []
        self.deletedItems = CatalogItemList(store = CatalogItem.Customization)

    def delete(self):
        for item in self.items:
            item.requestDelete()

        self.items = None
        self.director = None

        self.ignoreAll()

        DistributedObjectAI.delete(self)

    def setOwnerId(self):
        pass

    def setOwnerName(self):
        pass

    def setInteriorId(self):
        pass

    def getOwnerId(self):
        return self.house.avId

    def getOwnerName(self):
        return self.house.name

    def getInteriorId(self):
        return self.house.interior.do_id

    def getAtticItems(self):
        return self.house.getAtticItems()

    def d_setAtticItems(self, items):
        self.sendUpdate('setAtticItems', [items.getBlob(store = CatalogItem.Customization)])

    def d_setAtticWallpaper(self, items):
        self.sendUpdate('setAtticWallpaper', [items.getBlob(store = CatalogItem.Customization)])

    def getAtticWallpaper(self):
        return self.house.getAtticWallpaper()

    def d_setAtticWindows(self, items):
        self.sendUpdate('setAtticWindows', [items.getBlob(store = CatalogItem.Customization)])

    def getAtticWindows(self):
        return self.house.getAtticWindows()

    def setDeletedItems(self, deletedItems):
        self.deletedItems = CatalogItemList(deletedItems, store = CatalogItem.Customization)

    def getDeletedItems(self):
        deleted = self.house.reconsiderDeletedItems()

        if deleted:
            self.house.d_setDeletedItems(self.house.deletedItems)

        return self.house.deletedItems.getBlob(store = CatalogItem.Customization)

    def d_setDeletedItems(self, items):
        self.sendUpdate('setDeletedItems', [items.getBlob(store = CatalogItem.Customization)])