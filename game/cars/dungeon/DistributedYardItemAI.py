from game.cars.carplayer.InteractiveObjectAI import InteractiveObjectAI
from bson.objectid import ObjectId


class DistributedYardItemAI(InteractiveObjectAI):
    def __init__(self, air, itemId: int, catalogItemId: int, position: tuple) -> None:
        InteractiveObjectAI.__init__(self, air)

        self.itemId: int = itemId
        self.catalogItemId: int = catalogItemId
        self.position: tuple = position
        self.objectId: ObjectId = ObjectId()

    def getItemId(self) -> int:
        return self.itemId

    def getCatalogItemId(self) -> int:
        return self.catalogItemId

    def setPosition(self, x: int, y: int) -> None:
        self.position = (x, y)
        self.d_setPosition(x, y)

    def d_setPosition(self, x: int, y: int) -> None:
        self.sendUpdate("setPosition", [x, y])

    def getPosition(self) -> tuple:
        return self.position
