from . import CatalogItem
from direct.showbase import PythonUtil
from direct.gui.DirectGui import *

class CatalogAtticItem(CatalogItem.CatalogItem):

    def storedInAttic(self):
        return 1

    def isDeletable(self):
        return 1

    def getHouseInfo(self, avatar):
        houseId = avatar.houseId
        if not houseId:
            self.notify.warning('Avatar %s has no houseId associated.' % avatar.doId)
            return (None, ToontownGlobals.P_InvalidIndex)
        house = simbase.air.doId2do.get(houseId)
        if not house:
            self.notify.warning('House %s (for avatar %s) not instantiated.' % (houseId, avatar.doId))
            return (None, ToontownGlobals.P_InvalidIndex)
        numAtticItems = len(house.atticItems) + len(house.atticWallpaper) + len(house.atticWindows)
        numHouseItems = numAtticItems + len(house.interiorItems)
        if numHouseItems >= ToontownGlobals.MaxHouseItems and not self.replacesExisting():
            return (house, ToontownGlobals.P_NoRoomForItem)
        return (house, ToontownGlobals.P_ItemAvailable)
