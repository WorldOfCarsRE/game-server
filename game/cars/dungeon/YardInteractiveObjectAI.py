from game.cars.carplayer.InteractiveObjectAI import InteractiveObjectAI


class YardInteractiveObjectAI(InteractiveObjectAI):
    def __init__(self, air, catalogItemId: int) -> None:
        InteractiveObjectAI.__init__(self, air)

        self.catalogItemId: int = catalogItemId

    def getCatalogItemId(self) -> int:
        return self.catalogItemId
