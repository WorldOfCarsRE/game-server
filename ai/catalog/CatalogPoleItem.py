from . import CatalogItem
from ai.fishing.FishingAI import FishGlobals
from direct.actor import Actor

class CatalogPoleItem(CatalogItem.CatalogItem):
    sequenceNumber = 0

    def makeNewItem(self, rodId):
        self.rodId = rodId
        CatalogItem.CatalogItem.makeNewItem(self)

    def getPurchaseLimit(self):
        return 1

    def reachedPurchaseLimit(self, avatar):
        return avatar.getFishingRod() >= self.rodId or self in avatar.onOrder or self in avatar.mailboxContents

    def saveHistory(self):
        return 1

    def recordPurchase(self, avatar, optional):
        if self.rodId < 0 or self.rodId > FishGlobals.MaxRodId:
            self.notify.warning('Invalid fishing pole: %s for avatar %s' % (self.rodId, avatar.doId))
            return ToontownGlobals.P_InvalidIndex
        if self.rodId < avatar.getFishingRod():
            self.notify.warning('Avatar already has pole: %s for avatar %s' % (self.rodId, avatar.doId))
            return ToontownGlobals.P_ItemUnneeded
        avatar.b_setFishingRod(self.rodId)
        return ToontownGlobals.P_ItemAvailable

    def isGift(self):
        return 0

    def getDeliveryTime(self):
        return 24 * 60

    def output(self, store = -1):
        return 'CatalogPoleItem(%s%s)' % (self.rodId, self.formatOptionalData(store))


    def compareTo(self, other):
        return self.rodId - other.rodId

    def getHashContents(self):
        return self.rodId

    def decodeDatagram(self, di, versionNumber, store):
        CatalogItem.CatalogItem.decodeDatagram(self, di, versionNumber, store)
        self.rodId = di.getUint8()
        price = FishGlobals.RodPriceDict[self.rodId]

    def encodeDatagram(self, dg, store):
        CatalogItem.CatalogItem.encodeDatagram(self, dg, store)
        dg.addUint8(self.rodId)


def nextAvailablePole(avatar, duplicateItems):
    rodId = avatar.getFishingRod() + 1
    if rodId > FishGlobals.MaxRodId:
        return None
    item = CatalogPoleItem(rodId)
    while item in avatar.onOrder or item in avatar.mailboxContents:
        rodId += 1
        if rodId > FishGlobals.MaxRodId:
            return None
        item = CatalogPoleItem(rodId)

    return item


def getAllPoles():
    list = []
    for rodId in range(0, FishGlobals.MaxRodId + 1):
        list.append(CatalogPoleItem(rodId))

    return list
