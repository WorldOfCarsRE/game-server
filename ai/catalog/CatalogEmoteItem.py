from . import CatalogItem
from direct.interval.IntervalGlobal import *
LoyaltyEmoteItems = (20, 21, 22, 23, 24)

class CatalogEmoteItem(CatalogItem.CatalogItem):
    sequenceNumber = 0
    pictureToon = None

    def makeNewItem(self, emoteIndex, loyaltyDays = 0):
        self.emoteIndex = emoteIndex
        self.loyaltyDays = loyaltyDays
        CatalogItem.CatalogItem.makeNewItem(self)

    def getPurchaseLimit(self):
        return 1

    def reachedPurchaseLimit(self, avatar):
        if self in avatar.onOrder or self in avatar.mailboxContents or self in avatar.onGiftOrder or self in avatar.awardMailboxContents or self in avatar.onAwardOrder:
            return 1
        if self.emoteIndex >= len(avatar.emoteAccess):
            return 0
        return avatar.emoteAccess[self.emoteIndex] != 0

    def getAcceptItemErrorText(self, retcode):
        if retcode == ToontownGlobals.P_ItemAvailable:
            return TTLocalizer.CatalogAcceptEmote
        return CatalogItem.CatalogItem.getAcceptItemErrorText(self, retcode)

    def saveHistory(self):
        return 1

    def recordPurchase(self, avatar, optional):
        if self.emoteIndex < 0 or self.emoteIndex > len(avatar.emoteAccess):
            self.notify.warning('Invalid emote access: %s for avatar %s' % (self.emoteIndex, avatar.doId))
            return ToontownGlobals.P_InvalidIndex
        avatar.emoteAccess[self.emoteIndex] = 1
        avatar.d_setEmoteAccess(avatar.emoteAccess)
        return ToontownGlobals.P_ItemAvailable

    def output(self, store = -1):
        return 'CatalogEmoteItem(%s%s)' % (self.emoteIndex, self.formatOptionalData(store))

    def compareTo(self, other):
        return self.emoteIndex - other.emoteIndex

    def getHashContents(self):
        return self.emoteIndex

    def getBasePrice(self):
        return 550

    def decodeDatagram(self, di, versionNumber, store):
        CatalogItem.CatalogItem.decodeDatagram(self, di, versionNumber, store)
        self.emoteIndex = di.getUint8()
        if versionNumber >= 6:
            self.loyaltyDays = di.getUint16()
        else:
            self.loyaltyDays = 0
        if self.emoteIndex > len(OTPLocalizer.EmoteList):
            raise ValueError

    def encodeDatagram(self, dg, store):
        CatalogItem.CatalogItem.encodeDatagram(self, dg, store)
        dg.addUint8(self.emoteIndex)
        dg.addUint16(self.loyaltyDays)

    def isGift(self):
        if self.getEmblemPrices():
            return 0
        if self.loyaltyRequirement() > 0:
            return 0
        elif self.emoteIndex in LoyaltyEmoteItems:
            return 0
        else:
            return 1
