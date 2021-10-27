from . import CatalogItem
import time
from ai import ToontownGlobals

class CatalogRentalItem(CatalogItem.CatalogItem):

    def makeNewItem(self, typeIndex, duration, cost):
        self.typeIndex = typeIndex
        self.duration = duration
        self.cost = cost
        CatalogItem.CatalogItem.makeNewItem(self)

    def getRentalType(self):
        return self.typeIndex

    def getDuration(self):
        return self.duration

    def getPurchaseLimit(self):
        return 0

    def reachedPurchaseLimit(self, avatar):
        if self in avatar.onOrder or self in avatar.mailboxContents or self in avatar.onGiftOrder or self in avatar.awardMailboxContents or self in avatar.onAwardOrder:
            return 1
        return 0

    def saveHistory(self):
        return 1

    def recordPurchase(self, avatar, optional):
        self.notify.debug('rental -- record purchase')
        if avatar:
            self.notify.debug('rental -- has avater')
            estate = simbase.air.estateMgr.estate.get(avatar.do_id)
            if estate:
                self.notify.debug('rental -- has estate')
                estate.rentItem(self.typeIndex, self.duration)
            else:
                self.notify.debug('rental -- something not there')
        return ToontownGlobals.P_ItemAvailable

    def output(self, store = -1):
        return 'CatalogRentalItem(%s%s)' % (self.typeIndex, self.formatOptionalData(store))

    def compareTo(self, other):
        return self.typeIndex - other.typeIndex

    def getHashContents(self):
        return self.typeIndex

    def getBasePrice(self):
        if self.typeIndex == ToontownGlobals.RentalCannon:
            return self.cost
        elif self.typeIndex == ToontownGlobals.RentalGameTable:
            return self.cost
        else:
            return 50

    def decodeDatagram(self, di, versionNumber, store):
        CatalogItem.CatalogItem.decodeDatagram(self, di, versionNumber, store)
        if versionNumber >= 7:
            self.cost = di.getUint16()
        else:
            self.cost = 1000
        self.duration = di.getUint16()
        self.typeIndex = di.getUint16()

    def encodeDatagram(self, dg, store):
        CatalogItem.CatalogItem.encodeDatagram(self, dg, store)
        dg.addUint16(self.cost)
        dg.addUint16(self.duration)
        dg.addUint16(self.typeIndex)

    def getDeliveryTime(self):
        return 1

    def isRental(self):
        return 1


def getAllRentalItems():
    list = []
    for rentalType in (ToontownGlobals.RentalCannon,):
        list.append(CatalogRentalItem(rentalType, 2880, 1000))

    return list
