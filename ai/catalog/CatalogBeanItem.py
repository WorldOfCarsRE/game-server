from . import CatalogItem
from ai import ToontownGlobals

class CatalogBeanItem(CatalogItem.CatalogItem):
    sequenceNumber = 0

    def makeNewItem(self, beanAmount, tagCode = 1):
        self.beanAmount = beanAmount
        self.giftCode = tagCode
        CatalogItem.CatalogItem.makeNewItem(self)

    def getPurchaseLimit(self):
        return 0

    def reachedPurchaseLimit(self, avatar):
        if self in avatar.onOrder or self in avatar.mailboxContents or self in avatar.onGiftOrder or self in avatar.awardMailboxContents or self in avatar.onAwardOrder:
            return 1
        return 0

    def saveHistory(self):
        return 0

    def recordPurchase(self, avatar, optional):
        if avatar:
            avatar.addMoney(self.beanAmount)
        return ToontownGlobals.P_ItemAvailable

    def output(self, store = -1):
        return 'CatalogBeanItem(%s%s)' % (self.beanAmount, self.formatOptionalData(store))

    def compareTo(self, other):
        return self.beanAmount - other.beanAmount

    def getHashContents(self):
        return self.beanAmount

    def getBasePrice(self):
        return self.beanAmount

    def decodeDatagram(self, di, versionNumber, store):
        CatalogItem.CatalogItem.decodeDatagram(self, di, versionNumber, store)
        self.beanAmount = di.getUint16()

    def encodeDatagram(self, dg, store):
        CatalogItem.CatalogItem.encodeDatagram(self, dg, store)
        dg.addUint16(self.beanAmount)
