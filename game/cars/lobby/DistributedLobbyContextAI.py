from game.cars.lobby.DistributedLobbyAI import DistributedLobbyAI

from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.DistributedObjectAI import DistributedObjectAI
from typing import List

class DistributedLobbyContextAI(DistributedObjectAI):
    notify = directNotify.newCategory("DistributedLobbyContextAI")

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.playersInDungeon: List[int] = []
        self.playersInContext: List[int] = []
        self.lobby: DistributedLobbyAI = None

        self.destinationShard: int = 0
        self.destinationZone: int = 0

    def delete(self):
        if self in self.lobby.contexts:
            self.lobby.contexts.remove(self)
        for avId in self.playersInContext:
            self.ignore(self.air.getDeleteDoIdEvent(avId))

        DistributedObjectAI.delete(self)

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
        self.notify.debug(f"Player joined: {avId}, Total: {self.playersInContext}")
        self.playersInContext.append(avId)
        self.acceptOnce(self.air.getDeleteDoIdEvent(avId), self.removePlayerInContext, extraArgs=[avId])
        if self.isGenerated():
            self.d_setPlayersInContext(self.playersInContext)
            self.sendUpdate("setPlayerJoin", (avId,))

    def removePlayerInContext(self, avId):
        if avId not in self.playersInContext:
            return
        self.playersInContext.remove(avId)
        self.ignore(self.air.getDeleteDoIdEvent(avId))
        self.notify.debug(f"Player left: {avId}, Total: {self.playersInContext}")
        if self.isGenerated():
            self.d_setPlayersInContext(self.playersInContext)
            self.sendUpdate("setPlayerQuit", (avId,))

            if not self.playersInContext:
                self.notify.debug("Everybody left, deleting.")
                if self in self.lobby.contexts:
                    self.lobby.contexts.remove(self)
                self.requestDelete()

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
