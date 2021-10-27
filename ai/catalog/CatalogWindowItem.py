from panda3d.core import *
from . import CatalogAtticItem
from . import CatalogItem
WVTModelName = 0
WVTBasePrice = 1
WVTSkyName = 2
WindowViewTypes = {10: ('phase_5.5/models/estate/Garden1', 900, None),
 20: ('phase_5.5/models/estate/GardenA', 900, None),
 30: ('phase_5.5/models/estate/GardenB', 900, None),
 40: ('phase_5.5/models/estate/cityView', 900, None),
 50: ('phase_5.5/models/estate/westernView', 900, None),
 60: ('phase_5.5/models/estate/underwaterView', 900, None),
 70: ('phase_5.5/models/estate/tropicView', 900, None),
 80: ('phase_5.5/models/estate/spaceView', 900, None),
 90: ('phase_5.5/models/estate/PoolView', 900, None),
 100: ('phase_5.5/models/estate/SnowView', 900, None),
 110: ('phase_5.5/models/estate/FarmView', 900, None),
 120: ('phase_5.5/models/estate/IndianView', 900, None),
 130: ('phase_5.5/models/estate/WesternMainStreetView', 900, None)}

class CatalogWindowItem(CatalogAtticItem.CatalogAtticItem):

    def makeNewItem(self, windowType, placement = None):
        self.windowType = windowType
        self.placement = placement
        CatalogAtticItem.CatalogAtticItem.makeNewItem(self)

    def saveHistory(self):
        return 1

    def recordPurchase(self, avatar, optional):
        self.giftTag = None
        house, retcode = self.getHouseInfo(avatar)
        if retcode >= 0:
            house.addWindow(self)
        return retcode

    def getDeliveryTime(self):
        return 4 * 60

    def output(self, store = -1):
        return 'CatalogWindowItem(%s%s)' % (self.windowType, self.formatOptionalData(store))

    def formatOptionalData(self, store = -1):
        result = CatalogAtticItem.CatalogAtticItem.formatOptionalData(self, store)
        if store & CatalogItem.WindowPlacement and self.placement != None:
            result += ', placement = %s' % self.placement
        return result

    def compareTo(self, other):
        return self.windowType - other.windowType

    def getHashContents(self):
        return self.windowType

    def getBasePrice(self):
        return WindowViewTypes[self.windowType][WVTBasePrice]

    def decodeDatagram(self, di, versionNumber, store):
        CatalogAtticItem.CatalogAtticItem.decodeDatagram(self, di, versionNumber, store)
        self.placement = None
        if store & CatalogItem.WindowPlacement:
            self.placement = di.getUint8()
        self.windowType = di.getUint8()
        wvtype = WindowViewTypes[self.windowType]

    def encodeDatagram(self, dg, store):
        CatalogAtticItem.CatalogAtticItem.encodeDatagram(self, dg, store)
        if store & CatalogItem.WindowPlacement:
            dg.addUint8(self.placement)
        dg.addUint8(self.windowType)
