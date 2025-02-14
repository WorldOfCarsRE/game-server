from direct.distributed.DistributedObjectAI import DistributedObjectAI
from typing import List

class DistributedDungeonAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.playerIds: List[int] = []
        self.lobbyDoId: int = 0
        self.contextDoId: int = 0
        self.dungeonItemId: int = 1000
        self.interactiveObjects: list = []

    def getWaitForObjects(self):
        return [] # self.playerIds

    def getDungeonItemId(self):
        return self.dungeonItemId

    def getLobbyDoid(self):
        return self.lobbyDoId

    def getContextDoid(self):
        return self.contextDoId

    def setAiCommand(self, command, args):
        pass
