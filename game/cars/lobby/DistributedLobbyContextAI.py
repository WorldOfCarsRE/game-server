from game.cars.racing.DistributedLobbyAI import DistributedLobbyAI

from direct.distributed.DistributedObjectAI import DistributedObjectAI
from typing import List

class DistributedLobbyContextAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.playersInDungeon: List[int] = []
        self.playersInContext: List[int] = []
        self.lobby: DistributedLobbyAI = None

        self.destinationShard: int = 0
        self.destinationZone: int = 0

    def getPlayersInDungeon(self):
        return self.playersInDungeon

    def setPlayersInContext(self, players: List[int]):
        self.playersInContext = players

    def d_setPlayersInContext(self, players: List[int]):
        self.sendUpdate("setPlayersInContext", (players,))

    def b_setPlayersInContext(self, players: List[int]):
        self.setPlayersInContext(players)
        self.d_setPlayersInContext(players)

    def isAcceptingNewPlayers(self) -> bool:
        if self.playersInDungeon or len(self.playersInContext) >= 4:
            return False

        return True

    def addPlayerInContext(self, avId):
        if avId in self.playersInContext:
            return
        self.playersInContext.append(avId)
        if self.doId:
            self.d_setPlayersInContext(self.playersInContext)
            self.sendUpdate("setPlayerJoin", (avId,))

    def getPlayersInContext(self):
        return self.playersInContext

    def getOwner(self):
        return self.lobby.doId

    def b_setGotoDungeon(self, destinationShard: int, destinationZone: int):
        self.destinationShard = destinationShard
        self.destinationZone = destinationZone

        self.sendUpdate('gotoDungeon', [destinationShard, destinationZone])

    def getGotoDungeon(self):
        return self.destinationShard, self.destinationZone
