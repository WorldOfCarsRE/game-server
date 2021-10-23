from ai.DistributedObjectAI import DistributedObjectAI
from ai.house.DistributedHouseDoorAI import DistributedHouseDoorAI
from ai.house.DistributedHouseInteriorAI import DistributedHouseInteriorAI
from ai.building import DoorTypes
from ai.estate.DistributedMailboxAI import DistributedMailboxAI

class DistributedHouseAI(DistributedObjectAI):

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.housePos = 0
        self.houseType = 0
        self.gardenPos = 0
        self.avId = 0
        self.name = ''
        self.color = 0
        self.atticItems = ''
        self.interiorItems = ''
        self.atticWallpaper = ''
        self.interiorWallpaper = ''
        self.atticWindows = ''
        self.interiorWindows = ''
        self.deletedItems = ''
        self.cannonEnabled = 0
        self.interiorZoneId = 0
        self.door = None
        self.insideDoor = 0
        self.interior = None

    def announceGenerate(self):
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

        # Now tell the client that the house is ready.
        self.d_setHouseReady()

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
        return self.atticItems

    def getInteriorItems(self):
        return self.interiorItems

    def getAtticWallpaper(self):
        return self.atticWallpaper

    def getInteriorWallpaper(self):
        return self.interiorWallpaper

    def getAtticWindows(self):
        return self.atticWindows

    def getInteriorWindows(self):
        return self.interiorWindows

    def getDeletedItems(self):
        return self.deletedItems

    def getCannonEnabled(self) -> int:
        return self.cannonEnabled