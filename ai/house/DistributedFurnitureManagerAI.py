from ai.DistributedObjectAI import DistributedObjectAI
from ai.catalog.CatalogItemList import CatalogItemList
from ai.catalog import CatalogItem
from ai.house.DistributedBankAI import DistributedBankAI
from ai.house.WearableStorageAI import DistributedClosetAI, DistributedTrunkAI
from ai.house.DistributedPhoneAI import DistributedPhoneAI
from ai.house.DistributedFurnitureItemAI import DistributedFurnitureItemAI
from ai.catalog import CatalogFurnitureItem, CatalogSurfaceItem
from ai import ToontownGlobals

from direct.task import Task

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
        elif item.getFlags() & CatalogFurnitureItem.FLTrunk:
            cl = DistributedTrunkAI
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

    def requestControl(self, dfitem, directorAvId):
        # Returns true if the indicated director is allowed to move
        # the item, false otherwise.
        if self.dfitems == None or dfitem not in self.dfitems:
            return 0

        return directorAvId == self.director

    def saveItemPosition(self, dfitem):
        # Saves the position of the DistributedFurnitureItem in the
        # interior.
        if dfitem in self.dfitems:
            dfitem.item.posHpr = dfitem.posHpr
            self.house.interiorItems.markDirty()
            self.house.d_setInteriorItems(self.house.interiorItems)

    def moveItemToAtticMessage(self, doId, context):
        avId = self.air.currentAvatarSender
        retcode = self.__doMoveItemToAttic(avId, doId)
        self.sendUpdateToAvatar(avId, 'moveItemToAtticResponse', [retcode, context])

    def isHouseFull(self):
        numAtticItems = len(self.house.atticItems) + len(self.house.atticWallpaper) + len(self.house.atticWindows)
        numHouseItems = numAtticItems + len(self.house.interiorItems)
        return numHouseItems >= ToontownGlobals.MaxHouseItems

    def __doMoveItemToAttic(self, avId, doId):
        # A request by the client to move the indicated
        # DistributedFurnitureItem into the attic.
        if avId != self.director:
            return ToontownGlobals.FM_NotDirector

        dfitem = simbase.air.doTable.get(doId)

        if dfitem == None or dfitem not in self.dfitems:
            return ToontownGlobals.FM_InvalidIndex

        item = dfitem.item
        self.house.atticItems.append(item)

        # Find the item in self.house.interiorItems. We have to check for
        # exact equivalence.
        for i in range(len(self.house.interiorItems)):
            if self.house.interiorItems[i] is item:
                del self.house.interiorItems[i]
                break

        # Also remove it from self.dfitems.
        self.dfitems.remove(dfitem)
        item.dfitem = None

        self.house.d_setAtticItems(self.house.atticItems)
        self.house.d_setInteriorItems(self.house.interiorItems)

        dfitem.requestDelete()

        # Tell the client our new list of attic items.
        self.d_setAtticItems(self.house.atticItems)
        return ToontownGlobals.FM_MovedItem

    def moveItemFromAtticMessage(self, index, x, y, z, h, p, r, context):
        # A request by the client to move the indicated
        # item out of the attic and to the given position.
        avId = self.air.currentAvatarSender

        retcode, objectId = self.__doMoveItemFromAttic(avId, index, (x, y, z, h, p, r))
        taskMgr.doMethodLater(.5, self.__moveItemFromAtticResponse, f'moveItemFromAtticResponse-{objectId}', extraArgs = [avId, retcode, objectId, context], appendTask = False)

    def __moveItemFromAtticResponse(self, avId, retcode, objectId, context):
        if not self.deleted and objectId in self.air.doTable:
            self.sendUpdateToAvatar(avId, 'moveItemFromAtticResponse', [retcode, objectId, context])

        return Task.done

    def __doMoveItemFromAttic(self, avId, index, posHpr):
        if avId != self.director:
            return (ToontownGlobals.FM_NotDirector, 0)

        if index < 0 or index >= len(self.house.atticItems):
            return (ToontownGlobals.FM_InvalidIndex, 0)

        item = self.house.atticItems[index]
        del self.house.atticItems[index]

        item.posHpr = posHpr

        self.house.interiorItems.append(item)
        self.house.d_setInteriorItems(self.house.interiorItems)
        self.house.d_setAtticItems(self.house.atticItems)

        dfitem = self.manifestInteriorItem(item)

        if not dfitem:
            return (ToontownGlobals.FM_InvalidItem, 0)

        self.d_setAtticItems(self.house.atticItems)
        return (ToontownGlobals.FM_MovedItem, dfitem.do_id)

    def moveWallpaperFromAtticMessage(self, index, room, context):
        # A request by the client to swap the given wallpaper from the
        # attic with the interior wallpaper for the indicated room.
        avId = self.air.currentAvatarSender
        retcode = self.__doMoveWallpaperFromAttic(avId, index, room)
        self.sendUpdateToAvatarId(avId, 'moveWallpaperFromAtticResponse', [retcode, context])

    def __doMoveWallpaperFromAttic(self, avId, index, room):
        if avId != self.director:
            return ToontownGlobals.FM_NotDirector

        if index < 0 or index >= len(self.house.atticWallpaper):
            return ToontownGlobals.FM_InvalidIndex

        item = self.house.atticWallpaper[index]
        surface = item.getSurfaceType()
        slot = room * CatalogSurfaceItem.NUM_ST_TYPES + surface

        if slot < 0 or slot >= len(self.house.interiorWallpaper):
            return ToontownGlobals.FM_InvalidIndex

        repl = self.house.interiorWallpaper[slot]

        self.house.interiorWallpaper[slot] = item
        self.house.atticWallpaper[index] = repl
        self.house.d_setAtticWallpaper(self.house.atticWallpaper)
        self.house.d_setInteriorWallpaper(self.house.interiorWallpaper)
        return ToontownGlobals.FM_SwappedItem