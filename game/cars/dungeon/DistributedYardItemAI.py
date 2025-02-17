from game.cars.carplayer.InteractiveObjectAI import InteractiveObjectAI


class DistributedYardItemAI(InteractiveObjectAI):
    def __init__(self, air, itemId: int, catalogItemId: int, position: tuple) -> None:
        InteractiveObjectAI.__init__(self, air)

        self.itemId: int = itemId
        self.catalogItemId: int = catalogItemId
        self.position: tuple = position

    def getItemId(self) -> int:
        return self.itemId

    def getCatalogItemId(self) -> int:
        return self.catalogItemId

    def getPosition(self) -> tuple:
        return self.position
