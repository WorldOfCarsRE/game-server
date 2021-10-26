from ai.DistributedObjectAI import DistributedObjectAI
from ai.catalog.CatalogItemList import CatalogItemList
from ai.catalog import CatalogItem
from ai.house.DistributedBankAI import DistributedBankAI
from ai.house.DistributedClosetAI import DistributedClosetAI
from ai.house.DistributedPhoneAI import DistributedPhoneAI
from ai.house.DistributedFurnitureItemAI import DistributedFurnitureItemAI
from ai.catalog import CatalogFurnitureItem

class DistributedFurnitureManagerAI(DistributedObjectAI):

    def __init__(self, air, house, isInterior):
        DistributedObjectAI.__init__(self, air)

        self.house = house
        self.isInterior = isInterior
        self.director = 0
        self.dfitems = []
        self.deletedItems = CatalogItemList(store = CatalogItem.Customization)

    def delete(self):
        for dfitem in self.dfitems:
            dfitem.requestDelete()

        self.dfitems = None
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

    def manifestInteriorItem(self, item):
        # Creates and returns a DistributedFurnitureItem for the
        # indicated furniture item.

        if not hasattr(item, 'getFlags'):
            return None

        # Choose the appropriate kind of object to create.  Usually it
        # is just a DistributedFurnitureItemAI, but sometimes we have
        # to be more specific.
        if item.getFlags() & CatalogFurnitureItem.FLBank:
            cl = DistributedBankAI
        elif item.getFlags() & CatalogFurnitureItem.FLCloset:
            cl = DistributedClosetAI
        elif item.getFlags() & CatalogFurnitureItem.FLPhone:
            cl = DistributedPhoneAI
        else:
            cl = DistributedFurnitureItemAI

        dfitem = cl(self.air, self, item)
        dfitem.generateWithRequired(self.house.interiorZoneId)
        item.dfitem = dfitem
        self.dfitems.append(dfitem)

        # Send the initial position.
        dfitem.d_setPosHpr(*item.posHpr)
        return dfitem