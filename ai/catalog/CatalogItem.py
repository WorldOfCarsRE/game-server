from direct.directnotify import DirectNotifyGlobal
from pandac.PandaModules import *
from toontown.toonbase import TTLocalizer
from toontown.toonbase import ToontownGlobals
from direct.interval.IntervalGlobal import *
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
import sys
CatalogReverseType = None
CatalogItemVersion = 8
CatalogBackorderMarkup = 1.2
CatalogSaleMarkdown = 0.75
Customization = 1
DeliveryDate = 2
Location = 4
WindowPlacement = 8
GiftTag = 16
CatalogTypeUnspecified = 0
CatalogTypeWeekly = 1
CatalogTypeBackorder = 2
CatalogTypeMonthly = 3
CatalogTypeLoyalty = 4

class CatalogItem:
    notify = DirectNotifyGlobal.directNotify.newCategory('CatalogItem')

    def __init__(self, *args, **kw):
        self.saleItem = 0
        self.deliveryDate = None
        self.posHpr = None
        self.giftTag = None
        self.giftCode = 0
        self.hasPicture = False
        self.volume = 0
        self.specialEventId = 0
        if len(args) >= 1 and isinstance(args[0], DatagramIterator):
            self.decodeDatagram(*args, **kw)
        else:
            self.makeNewItem(*args, **kw)
        return

    def isAward(self):
        result = self.specialEventId != 0
        return result

    def makeNewItem(self):
        pass

    def needsCustomize(self):
        return 0

    def saveHistory(self):
        return 0

    def getBackSticky(self):
        itemType = 0
        numSticky = 0
        return (itemType, numSticky)

    def putInBackCatalog(self, backCatalog, lastBackCatalog):
        if self.saveHistory() and not self.isSaleItem():
            if self not in backCatalog:
                if self in lastBackCatalog:
                    lastBackCatalog.remove(self)
                backCatalog.append(self)

    def replacesExisting(self):
        return 0

    def hasExisting(self):
        return 0

    def getYourOldDesc(self):
        return None

    def storedInCloset(self):
        return 0

    def storedInTrunk(self):
        return 0

    def storedInAttic(self):
        return 0

    def notOfferedTo(self, avatar):
        return 0

    def getPurchaseLimit(self):
        return 0

    def reachedPurchaseLimit(self, avatar):
        return 0

    def hasBeenGifted(self, avatar):
        if avatar.onGiftOrder.count(self) != 0:
            return 1
        return 0

    def recordPurchase(self, avatar, optional):
        self.notify.warning('%s has no purchase method.' % self)
        return ToontownGlobals.P_NoPurchaseMethod

    def isSaleItem(self):
        return self.saleItem

    def isGift(self):
        if self.getEmblemPrices():
            return 0
        return 1

    def isRental(self):
        return 0

    def forBoysOnly(self):
        return 0

    def forGirlsOnly(self):
        return 0

    def setLoyaltyRequirement(self, days):
        self.loyaltyDays = days

    def loyaltyRequirement(self):
        if not hasattr(self, 'loyaltyDays'):
            return 0
        else:
            return self.loyaltyDays

    def getPrice(self, catalogType):
        if catalogType == CatalogTypeBackorder:
            return self.getBackPrice()
        elif self.isSaleItem():
            return self.getSalePrice()
        else:
            return self.getCurrentPrice()

    def getCurrentPrice(self):
        return int(self.getBasePrice())

    def getBackPrice(self):
        return int(self.getBasePrice() * CatalogBackorderMarkup)

    def getSalePrice(self):
        return int(self.getBasePrice() * CatalogSaleMarkdown)

    def getDeliveryTime(self):
        return 0

    def output(self, store = -1):
        return 'CatalogItem'

    def formatOptionalData(self, store = -1):
        result = ''
        if store & Location and self.posHpr != None:
            result += ', posHpr = (%s, %s, %s, %s, %s, %s)' % self.posHpr
        return result

    def __str__(self):
        return self.output()

    def __repr__(self):
        return self.output()

    def compareTo(self, other):
        return 0

    def getHashContents(self):
        return None

    def __cmp__(self, other):
        c = cmp(self.__class__, other.__class__)
        if c != 0:
            return c
        return self.compareTo(other)

    def __hash__(self):
        return hash((self.__class__, self.getHashContents()))

    def getBasePrice(self):
        return 0

    def getEmblemPrices(self):
        return ()

    def decodeDatagram(self, di, versionNumber, store):
        if store & DeliveryDate:
            self.deliveryDate = di.getUint32()
        if store & Location:
            x = di.getArg(STInt16, 10)
            y = di.getArg(STInt16, 10)
            z = di.getArg(STInt16, 100)
            if versionNumber < 2:
                h = di.getArg(STInt16, 10)
                p = 0.0
                r = 0.0
            elif versionNumber < 5:
                h = di.getArg(STInt8, 256.0 / 360.0)
                p = di.getArg(STInt8, 256.0 / 360.0)
                r = di.getArg(STInt8, 256.0 / 360.0)
                hpr = oldToNewHpr(VBase3(h, p, r))
                h = hpr[0]
                p = hpr[1]
                r = hpr[2]
            else:
                h = di.getArg(STInt8, 256.0 / 360.0)
                p = di.getArg(STInt8, 256.0 / 360.0)
                r = di.getArg(STInt8, 256.0 / 360.0)
            self.posHpr = (x,
             y,
             z,
             h,
             p,
             r)
        if store & GiftTag:
            self.giftTag = di.getString()
        if versionNumber >= 8:
            self.specialEventId = di.getUint8()
        else:
            self.specialEventId = 0

    def encodeDatagram(self, dg, store):
        if store & DeliveryDate:
            dg.addUint32(self.deliveryDate)
        if store & Location:
            dg.putArg(self.posHpr[0], STInt16, 10)
            dg.putArg(self.posHpr[1], STInt16, 10)
            dg.putArg(self.posHpr[2], STInt16, 100)
            dg.putArg(self.posHpr[3], STInt8, 256.0 / 360.0)
            dg.putArg(self.posHpr[4], STInt8, 256.0 / 360.0)
            dg.putArg(self.posHpr[5], STInt8, 256.0 / 360.0)
        if store & GiftTag:
            dg.addString(self.giftTag)
        dg.addUint8(self.specialEventId)

    def getTypeCode(self):
        from . import CatalogItemTypes
        return CatalogItemTypes.CatalogItemTypes[self.__class__]

    def getBlob(self, store = 0):
        dg = PyDatagram()
        dg.addUint8(CatalogItemVersion)
        encodeCatalogItem(dg, self, store)
        return dg.getMessage()

    def getRequestPurchaseErrorTextTimeout(self):
        return 6

    def getDaysToGo(self, avatar):
        accountDays = avatar.getAccountDays()
        daysToGo = self.loyaltyRequirement() - accountDays
        if daysToGo < 0:
            daysToGo = 0
        return int(daysToGo)


def encodeCatalogItem(dg, item, store):
    from . import CatalogItemTypes
    flags = item.getTypeCode()
    if item.isSaleItem():
        flags |= CatalogItemTypes.CatalogItemSaleFlag
    if item.giftTag != None:
        flags |= CatalogItemTypes.CatalogItemGiftTag
    dg.addUint8(flags)
    if item.giftTag != None:
        dg.addUint32(item.giftTag)
        if not item.giftCode:
            item.giftCode = 0
        dg.addUint8(item.giftCode)
    item.encodeDatagram(dg, store)
    return


def decodeCatalogItem(di, versionNumber, store):
    global CatalogReverseType
    from . import CatalogItemTypes
    if CatalogReverseType == None:
        CatalogReverseType = {}
        for itemClass, index in list(CatalogItemTypes.CatalogItemTypes.items()):
            CatalogReverseType[index] = itemClass

    startIndex = di.getCurrentIndex()
    try:
        flags = di.getUint8()
        typeIndex = flags & CatalogItemTypes.CatalogItemTypeMask
        gift = None
        code = None
        if flags & CatalogItemTypes.CatalogItemGiftTag:
            gift = di.getUint32()
            code = di.getUint8()
        itemClass = CatalogReverseType[typeIndex]
        item = itemClass(di, versionNumber, store=store)
    except Exception as e:
        CatalogItem.notify.warning('Invalid catalog item in stream: %s, %s' % (sys.exc_info()[0], e))
        d = Datagram(di.getDatagram().getMessage()[startIndex:])
        d.dumpHex(Notify.out())
        from . import CatalogInvalidItem
        return CatalogInvalidItem.CatalogInvalidItem()

    if flags & CatalogItemTypes.CatalogItemSaleFlag:
        item.saleItem = 1
    item.giftTag = gift
    item.giftCode = code
    return item


def getItem(blob, store = 0):
    dg = PyDatagram(blob)
    di = PyDatagramIterator(dg)
    try:
        versionNumber = di.getUint8()
        return decodeCatalogItem(di, versionNumber, store)
    except Exception as e:
        CatalogItem.notify.warning('Invalid catalog item: %s, %s' % (sys.exc_info()[0], e))
        dg.dumpHex(Notify.out())
        from . import CatalogInvalidItem
        return CatalogInvalidItem.CatalogInvalidItem()
