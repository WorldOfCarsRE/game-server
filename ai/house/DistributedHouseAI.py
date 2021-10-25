from ai.DistributedObjectAI import DistributedObjectAI
from ai.house.DistributedHouseDoorAI import DistributedHouseDoorAI
from ai.house.DistributedHouseInteriorAI import DistributedHouseInteriorAI
from ai.building import DoorTypes
from ai.estate.DistributedMailboxAI import DistributedMailboxAI
from ai.house.DistributedFurnitureManagerAI import DistributedFurnitureManagerAI
from ai.catalog.CatalogItemList import CatalogItemList
from ai.catalog import CatalogItem
from ai.catalog.CatalogFurnitureItem import CatalogFurnitureItem
from ai.catalog import CatalogWallpaperItem, CatalogMouldingItem, CatalogFlooringItem, CatalogWainscotingItem
import time, random

class DistributedHouseAI(DistributedObjectAI):

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.housePos = 0
        self.houseType = 0
        self.gardenPos = 0
        self.avId = 0
        self.name = ''
        self.interiorWallpaper = CatalogItemList()
        self.atticWindows = CatalogItemList()
        self.interiorWindows = CatalogItemList()
        self.deletedItems = CatalogItemList()
        self.cannonEnabled = 0
        self.interiorZoneId = 0
        self.door = None
        self.insideDoor = 0
        self.interior = None
        self.interiorManager = None

    def announceGenerate(self):
        if self.avId and len(self.interiorWallpaper) == 0 and len(self.interiorWindows) == 0:
            # This is a newly-occupied house. We should set up initial
            # furniture for it.
            self.setInitialFurniture()

        # Toon interior:
        self.interiorZoneId = self.air.allocateZone()

        # Outside mailbox (if we have one)
        if self.avId:
            self.mailbox = DistributedMailboxAI(self.air, self)
            self.mailbox.generateWithRequired(self.zoneId)

        # Outside door:
        self.door = DistributedHouseDoorAI(self.air, self.do_id, DoorTypes.EXT_STANDARD)

        # Inside door of the same door (different zone, and different distributed object):
        self.insideDoor = DistributedHouseDoorAI(self.air, self.do_id, DoorTypes.INT_STANDARD)

        # Tell them about each other:
        self.door.setOtherDoor(self.insideDoor)
        self.insideDoor.setOtherDoor(self.door)
        self.door.zoneId = self.zoneId
        self.insideDoor.zoneId = self.interiorZoneId

        # Now that they both now about each other, generate them:
        self.door.generateWithRequired(self.zoneId)
        self.insideDoor.generateWithRequired(self.interiorZoneId)

        # Setup interior:
        self.interior = DistributedHouseInteriorAI(self.air, self)
        self.interior.setHouseIndex(self.housePos)
        self.interior.setHouseId(self.do_id)
        self.interior.generateWithRequired(self.interiorZoneId)

        self.resetFurniture()

        # Now tell the client that the house is ready.
        self.d_setHouseReady()

    def resetFurniture(self):
        # Deletes all of the furniture, wallpaper, and window items, and
        # recreates it all.

        if self.interiorManager != None:
            self.interiorManager.requestDelete()
            self.interiorManager = None

        # Create a furniture manager for the interior furniture.
        self.interiorManager = DistributedFurnitureManagerAI(self.air, self, 1)
        self.interiorManager.generateWithRequired(self.interiorZoneId)

        # Create all of the furniture items inside the house.
        for item in self.interiorItems:
            self.interiorManager.manifestInteriorItem(item)

        # Force the wallpaper and windows to be reissued to the
        # interior.
        self.interior.b_setWallpaper(self.interiorWallpaper)
        self.interior.b_setWindows(self.interiorWindows)

    def setInitialFurniture(self):
        # Resets the furniture to the initial default furniture for an
        # avatar.  Normally this is called only when the house is
        # first assigned, and for debugging.

        avatar = self.air.doTable.get(self.avId)

        # Boys are given the boy wardrobe initially, while girls are
        # given the girl wardrobe.
        wardrobeItem = 500
        if avatar and avatar.getStyle().gender == 'f':
            wardrobeItem = 510

        InitialFurnitureA = CatalogItemList([
            CatalogFurnitureItem(200, posHpr = (-23.618, 16.1823, 0.025, 90, 0, 0)),
            CatalogFurnitureItem(wardrobeItem, posHpr = (-22.5835, 21.8784, 0.025, 90, 0, 0)),
            CatalogFurnitureItem(1300, posHpr = (-21.4932, 5.76027, 0.025, 120, 0, 0)),
            CatalogFurnitureItem(400, posHpr = (-18.6, -12.0, 0.025, 90.0, 0.0, 0.0)),
            CatalogFurnitureItem(100, posHpr = (-18.9, -20.5, 0.025, 90.0, 0.0, 0.0)),
            CatalogFurnitureItem(100, posHpr = (-18.9, -3.5, 0.025, 90.0, 0.0, 0.0)),
            CatalogFurnitureItem(700, posHpr = (-3.34375, 22.3644, 0.025, -90, 0, 0)),
            CatalogFurnitureItem(710, posHpr = (0, -23, 0.025, 180, 0, 0)),
            CatalogFurnitureItem(700, posHpr = (4.44649, -0.463924, 0.025, 0, 0, 0)),
            CatalogFurnitureItem(1399, posHpr = (-10.1, 2.0, 0.1, 0, 0, 0)),
            ])

        InitialFurnitureB = CatalogItemList([
            CatalogFurnitureItem(200, posHpr = (-3.2, 17.0, 0.025, -0.2, 0.0, 0.0)),
            CatalogFurnitureItem(400, posHpr = (-18.6, -7.1, 0.025, 90.0, 0.0, 0.0)),
            CatalogFurnitureItem(700, posHpr = (3.6, -23.7, 0.025, 179.9, 0.0, 0.0)),
            CatalogFurnitureItem(710, posHpr = (-16.6, -19.1, 0.025, 90.0, 0.0, 0.0)),
            CatalogFurnitureItem(700, posHpr = (-1.8, -23.6, 0.025, 179.9, 0.0, 0.0)),
            CatalogFurnitureItem(wardrobeItem, posHpr = (-20.1, 4.4, 0.025, -180.0, 0.0, 0.0)),
            CatalogFurnitureItem(100, posHpr = (-1.1, 22.4, 0.025, -90.2, 0.0, 0.0)),
            CatalogFurnitureItem(1300, posHpr = (-21.7, 19.5, 0.025, 90.0, 0.0, 0.0)),
            CatalogFurnitureItem(100, posHpr = (4.0, 1.9, 0.025, -0.1, 0.0, 0.0)),
            CatalogFurnitureItem(1399, posHpr = (-10.1, 2.0, 0.1, 0, 0, 0)),
            ])

        InitialFurnitureC = CatalogItemList([
            CatalogFurnitureItem(200, posHpr = (-22.1, 6.5, 0.025, 90.0, 0.0, 0.0)),
            CatalogFurnitureItem(400, posHpr = (-0.2, -25.7, 0.025, 179.9, 0.0, 0.0)),
            CatalogFurnitureItem(710, posHpr = (-16.6, -12.2, 0.025, 90.0, 0.0, 0.0)),
            CatalogFurnitureItem(wardrobeItem, posHpr = (-4.7, 24.5, 0.025, 0.0, 0.0, 0.0)),
            CatalogFurnitureItem(1300, posHpr = (-20.5, 22.3, 0.025, 45.0, 0.0, 0.0)),
            CatalogFurnitureItem(100, posHpr = (-12.0, 25.9, 0.025, 0.0, 0.0, 0.0)),
            CatalogFurnitureItem(700, posHpr = (9.4, -8.6, 0.025, 67.5, 0.0, 0.0)),
            CatalogFurnitureItem(700, posHpr = (9.7, -15.1, 0.025, 112.5, 0.0, 0.0)),
            CatalogFurnitureItem(100, posHpr = (-14.7, 1.88, 0.025, 0.0, 0.0, 0.0)),
            CatalogFurnitureItem(1399, posHpr = (-10.1, 2.0, 0.1, 0, 0, 0)),
        ])

        self.b_setDeletedItems(CatalogItemList())
        self.b_setAtticItems(CatalogItemList())
        self.b_setInteriorItems(random.choice((InitialFurnitureA,
                                               InitialFurnitureB,
                                               InitialFurnitureC,
                                               )))
        self.b_setAtticWallpaper(CatalogItemList())

        # Choose a random set of wallpapers, and use the same set for
        # both rooms.
        wallpaper = [
            # Wallpaper
            random.choice(CatalogWallpaperItem.getWallpaperRange(1000,1299)),
            # Moulding
            random.choice(CatalogMouldingItem.getAllMouldings(1000, 1010)),
            # Flooring
            random.choice(CatalogFlooringItem.getAllFloorings(1000, 1010)),
            # Wainscoting
            random.choice(CatalogWainscotingItem.getAllWainscotings(1000, 1010)),
            ]

        self.b_setInteriorWallpaper(CatalogItemList(wallpaper + wallpaper))
        self.b_setAtticWindows(CatalogItemList())

        # Everyone starts out with a simple garden view, twice.
        self.b_setInteriorWindows(CatalogItemList([
            CatalogWindowItem(20, placement = 2),
            CatalogWindowItem(20, placement = 4),
            ]))

    def d_setHouseReady(self):
        self.sendUpdate('setHouseReady', [])

    def setHousePos(self, housePos):
        self.housePos = housePos

    def d_setHousePos(self, housePos):
        self.sendUpdate('setHousePos', [housePos])

    def b_setHousePos(self, housePos):
        self.setHousePos(housePos)
        self.d_setHousePos(housePos)

    def getHousePos(self) -> int:
        return self.housePos

    def getHouseType(self) -> int:
        return self.houseType

    def getGardenPos(self) -> int:
        return self.gardenPos

    def setAvatarId(self, avId):
        self.avId = avId

    def getAvatarId(self) -> int:
        return self.avId

    def getName(self) -> str:
        return self.name

    def getColor(self) -> int:
        return self.color

    def getAtticItems(self):
        return self.atticItems.getBlob(store = CatalogItem.Customization)

    def getInteriorItems(self):
        return self.interiorItems.getBlob(store = CatalogItem.Location | CatalogItem.Customization)

    def setAtticWallpaper(self, items):
        self.atticWallpaper = CatalogItemList(items, store = CatalogItem.Customization)

    def getAtticWallpaper(self):
        return self.atticWallpaper.getBlob(store = CatalogItem.Customization)

    def setInteriorWallpaper(self, items):
        self.interiorWallpaper = CatalogItemList(items, store = CatalogItem.Customization)

    def getInteriorWallpaper(self):
        return self.interiorWallpaper.getBlob(store = CatalogItem.Customization)

    def getAtticWindows(self):
        return self.atticWindows.getBlob(store = CatalogItem.Customization)

    def getInteriorWindows(self):
        return self.interiorWindows.getBlob(store = CatalogItem.Customization | CatalogItem.WindowPlacement)

    def getDeletedItems(self):
        return self.deletedItems.getBlob(store = CatalogItem.Customization | CatalogItem.DeliveryDate)

    def reconsiderDeletedItems(self):
        # Removes items from the deletedItems list whose expiration
        # time has expired. Returns the list of deleted items.

        # Get the current time in minutes.
        now = (int)(time.time() / 60 + 0.5)

        deleted, remaining = self.deletedItems.extractDeliveryItems(now)

        self.deletedItems = remaining

        return deleted

    def getCannonEnabled(self) -> int:
        return self.cannonEnabled

    def setDeletedItems(self, items):
        self.deletedItems = CatalogItemList(items, store = CatalogItem.Customization | CatalogItem.DeliveryDate)

        if self.air.doLiveUpdates:
            deleted = self.reconsiderDeletedItems()

            # If we removed any deleted items, immediately send the new
            # list back to the database.
            if deleted:
                self.d_setDeletedItems(self.deletedItems)

                if self.interiorManager:
                    self.interiorManager.d_setDeletedItems(self.deletedItems)

    def b_setDeletedItems(self, items):
        self.setDeletedItems(items)
        self.d_setDeletedItems(items)

    def b_setAtticItems(self, items):
        self.setAtticItems(items)
        self.d_setAtticItems(items)

    def d_setAtticItems(self, items):
        self.sendUpdate('setAtticItems', [items.getBlob(store = CatalogItem.Customization)])

    def setAtticItems(self, items):
        self.atticItems = CatalogItemList(items, store = CatalogItem.Customization)

    def b_setInteriorItems(self, items):
        self.setInteriorItems(items)
        self.d_setInteriorItems(items)

    def d_setInteriorItems(self, items):
        self.sendUpdate('setInteriorItems', [items.getBlob(store = CatalogItem.Location | CatalogItem.Customization)])

    def b_setAtticWallpaper(self, items):
        self.setAtticWallpaper(items)
        self.d_setAtticWallpaper(items)

    def b_setInteriorWallpaper(self, items):
        self.setInteriorWallpaper(items)
        self.d_setInteriorWallpaper(items)

    def d_setInteriorWallpaper(self, items):
        self.sendUpdate('setInteriorWallpaper', [items.getBlob(store = CatalogItem.Customization)])

        if self.interior:
            self.interior.b_setWallpaper(items)

    def b_setAtticWindows(self, items):
        self.setAtticWindows(items)
        self.d_setAtticWindows(items)

    def setInteriorWindows(self, items):
        self.interiorWindows = CatalogItemList(items, store = CatalogItem.Customization | CatalogItem.WindowPlacement)

    def b_setInteriorWindows(self, items):
        self.setInteriorWindows(items)
        self.d_setInteriorWindows(items)

    def d_setInteriorWindows(self, items):
        self.sendUpdate('setInteriorWindows', [items.getBlob(store = CatalogItem.Customization | CatalogItem.WindowPlacement)])

        if self.interior:
            self.interior.b_setWindows(items)

    def d_setDeletedItems(self, items):
        self.sendUpdate('setDeletedItems', [items.getBlob(store = CatalogItem.Customization | CatalogItem.DeliveryDate)])

    def setInteriorItems(self, items):
        # This should only be called once, to fill the data from the
        # database.  Subsequently, we should modify the list directly,
        # so we don't break the connection between items on the list
        # and manifested DistributedFurnitureItems.
        self.interiorItems = CatalogItemList(items, store = CatalogItem.Location | CatalogItem.Customization)

    def d_setAtticWallpaper(self, items):
        self.sendUpdate('setAtticWallpaper', [items.getBlob(store = CatalogItem.Customization)])

        if self.interiorManager:
            self.interiorManager.d_setAtticWallpaper(items)