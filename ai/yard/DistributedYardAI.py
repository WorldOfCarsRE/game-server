from ai.dungeon.DistributedDungeonAI import DistributedDungeonAI

class DistributedYardAI(DistributedDungeonAI):
    def __init__(self, air):
        DistributedDungeonAI.__init__(self, air)
        self.owner = 0

    def getOwner(self):
        return self.owner
