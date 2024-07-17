from direct.distributed.DistributedObjectAI import DistributedObjectAI
from typing import List

class DistributedLobbyContextAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.playersInDungeon: List[int] = []
        self.playersInContext: List[int] = []
        self.owningAv: int = 0

        self.destinationShard: int = 0
        self.destinationZone: int = 0

    def getPlayersInDungeon(self):
        return self.playersInDungeon

    def getPlayersInContext(self):
        return self.playersInContext

    def getOwner(self):
        return self.owningAv

    def b_setGotoDungeon(self, destinationShard: int, destinationZone: int):
        self.destinationShard = destinationShard
        self.destinationZone = destinationZone

        self.sendUpdate('gotoDungeon', [destinationShard, destinationZone])

    def getGotoDungeon(self):
        return self.destinationShard, self.destinationZone
