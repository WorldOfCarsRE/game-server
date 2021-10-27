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

    def suggestDirector(self, avId):
        # This method is sent by the client to request the right to
        # manipulate the controls, for the requestor or for another.
        # The AI decides whether to honor the request or ignore it.

        if self.dfitems == None:
            return

        # validate the avId
        avatar = self.air.doTable.get(avId)

        if (avId != 0) and (not avatar):
            # Note: avId == 0 OK since that signals end of furniture arranging
            return

        # The request is honored if the sender is the owner or is the
        # current director
        senderId = self.air.currentAvatarSender

        if senderId == self.house.avId or senderId == self.director:
            self.b_setDirector(avId)

    def b_setDirector(self, avId):
        self.setDirector(avId)
        self.d_setDirector(avId)

    def d_setDirector(self, avId):
        self.sendUpdate('setDirector', [avId])

    def setDirector(self, avId):
        if self.director != avId:
            # Go through the dfitems list and stop accepting
            # messages from the current director, if any.
            for dfitem in self.dfitems:
                dfitem.removeDirector()

            self.director = avId

    def setDirector(self, avId):
        if self.director != avId:
            # Go through the dfitems list and stop accepting
            # messages from the current director, if any.
            for dfitem in self.dfitems:
                dfitem.removeDirector()

            self.director = avId

    def avatarEnter(self):
        # Sent from the client when he enters furniture moving mode.
        avId = self.air.currentAvatarSender
        avatar = self.air.doTable.get(avId)

        if avatar:
            avatar.b_setGhostMode(1)

    def avatarExit(self):
        # Sent from the client when he enters furniture moving mode.
        avId = self.air.currentAvatarSender
        avatar = self.air.doTable.get(avId)

        if avatar:
            avatar.b_setGhostMode(0)