from . import CatalogItem
import time

class CatalogGardenStarterItem(CatalogItem.CatalogItem):

    def makeNewItem(self):
        CatalogItem.CatalogItem.makeNewItem(self)

    def getPurchaseLimit(self):
        return 0

    def reachedPurchaseLimit(self, avatar):
        if self in avatar.onOrder or self in avatar.mailboxContents or self in avatar.onGiftOrder or self in avatar.awardMailboxContents or self in avatar.onAwardOrder or hasattr(avatar, 'gardenStarted') and avatar.getGardenStarted():
            return 1
        return 0

    def saveHistory(self):
        return 1

    def recordPurchase(self, avatar, optional):
        print('rental-- record purchase')
        if avatar:
            print('starter garden-- has avater')
            estate = simbase.air.estateMgr.estate.get(avatar.do_id)
            if estate:
                print('starter garden-- has estate')
                estate.placeStarterGarden(avatar.do_id)
            else:
                print('starter garden-- something not there')
        return ToontownGlobals.P_ItemAvailable

    def output(self, store = -1):
        return 'CatalogGardenStarterItem(%s)' % self.formatOptionalData(store)

    def compareTo(self, other):
        return 0

    def getHashContents(self):
        return 0

    def getBasePrice(self):
        return 50

    def decodeDatagram(self, di, versionNumber, store):
        CatalogItem.CatalogItem.decodeDatagram(self, di, versionNumber, store)

    def encodeDatagram(self, dg, store):
        CatalogItem.CatalogItem.encodeDatagram(self, dg, store)

    def getDeliveryTime(self):
        return 1

    def isRental(self):
        return 0

    def isGift(self):
        return 0
