from .DistributedDungeonAI import DistributedDungeonAI

class DistributedYardAI(DistributedDungeonAI):
    def __init__(self, air):
        DistributedDungeonAI.__init__(self, air)

        self.dungeonItemId: int = 10001
        self.owner: int = 0

    def getOwner(self) -> int:
        return self.owner
