from . import CatalogItem
from ai import ToontownGlobals

class CatalogNametagItem(CatalogItem.CatalogItem):
    sequenceNumber = 0

    def makeNewItem(self, nametagStyle):
        self.nametagStyle = nametagStyle
        CatalogItem.CatalogItem.makeNewItem(self)

    def getPurchaseLimit(self):
        return 1

    def reachedPurchaseLimit(self, avatar):
        if self in avatar.onOrder or self in avatar.mailboxContents or self in avatar.onGiftOrder or self in avatar.awardMailboxContents or self in avatar.onAwardOrder:
            return 1
        if avatar.nametagStyle == self.nametagStyle:
            return 1
        return 0

    def getAcceptItemErrorText(self, retcode):
        if retcode == ToontownGlobals.P_ItemAvailable:
            return TTLocalizer.CatalogAcceptNametag
        return CatalogItem.CatalogItem.getAcceptItemErrorText(self, retcode)

    def saveHistory(self):
        return 1

    def recordPurchase(self, avatar, optional):
        if avatar:
            avatar.b_setNametagStyle(self.nametagStyle)
        return ToontownGlobals.P_ItemAvailable

    def output(self, store = -1):
        return 'CatalogNametagItem(%s%s)' % (self.nametagStyle, self.formatOptionalData(store))

    def compareTo(self, other):
        return self.nametagStyle - other.nametagStyle

    def getHashContents(self):
        return self.nametagStyle

    def getBasePrice(self):
        return 500
        cost = 500
        if self.nametagStyle == 0:
            cost = 600
        elif self.nametagStyle == 1:
            cost = 600
        elif self.nametagStyle == 2:
            cost = 600
        elif self.nametagStyle == 100:
            cost = 50
        return cost

    def decodeDatagram(self, di, versionNumber, store):
        CatalogItem.CatalogItem.decodeDatagram(self, di, versionNumber, store)
        self.nametagStyle = di.getUint16()

    def encodeDatagram(self, dg, store):
        CatalogItem.CatalogItem.encodeDatagram(self, dg, store)
        dg.addUint16(self.nametagStyle)

    def isGift(self):
        return 0

    def getBackSticky(self):
        itemType = 1
        numSticky = 4
        return (itemType, numSticky)
