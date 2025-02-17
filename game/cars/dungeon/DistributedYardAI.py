from .DistributedDungeonAI import DistributedDungeonAI
from .DistributedYardItemAI import DistributedYardItemAI
from game.cars.distributed.CarsGlobals import DEFAULT_DUNGEON_ZONE

RESPONSE_SUCCESS = 1
RESPONSE_NO_MORE_OF_THAT_ITEM = 2
RESPONSE_CANT_ADD_MORE_ITEMS = 3
RESPONSE_CANT_MODIFY_OWN_YARD = 4


class DistributedYardAI(DistributedDungeonAI):
    def __init__(self, air, owner: int):
        DistributedDungeonAI.__init__(self, air)

        self.dungeonItemId: int = 10001
        self.owner: int = owner
        self.objects: list = []

    def getOwner(self) -> int:
        return self.owner

    def addItemRequest(self, itemId: int, x: int, y: int, handle: int) -> None:
        av = self.air.getDo(self.getOwner())

        yardStocks: list = av.getYardStocks()

        for i, yardItem in enumerate(yardStocks):
            catalogItemId, quantity, usedQuantity = yardItem
            hasSomeOfItem: bool = quantity > 0

            if catalogItemId == itemId and hasSomeOfItem:
                yardStocks[i] = (itemId, quantity - 1, usedQuantity + 1)

                self.air.mongoInterface.mongodb.activeyarditems.insert_one(
                    {
                        "ownerDoId": self.getOwner(),
                        "itemId": catalogItemId,
                        "catalogItemId": catalogItemId,
                        "x": x,
                        "y": y
                    }
                )

                item = DistributedYardItemAI(self.air, catalogItemId, catalogItemId, (x, y))
                item.generateOtpObject(self.doId, DEFAULT_DUNGEON_ZONE)
                self.objects.append(item)

        av.setYardStocks(yardStocks)

        self.sendUpdateToAvatarId(self.getOwner(), "addItemResponse", [RESPONSE_SUCCESS if hasSomeOfItem else RESPONSE_NO_MORE_OF_THAT_ITEM, handle])

    def createObjects(self) -> None:
        activeYardItems = self.air.mongoInterface.retrieveFields("activeyarditems", self.getOwner())

        for yardItem in activeYardItems:
            item = DistributedYardItemAI(self.air, yardItem["itemId"], yardItem["catalogItemId"], (yardItem["x"], yardItem["y"]))
            item.generateOtpObject(self.doId, DEFAULT_DUNGEON_ZONE)
            self.objects.append(item)
