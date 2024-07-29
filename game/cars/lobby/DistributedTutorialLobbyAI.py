from game.cars.lobby.DistributedLobbyAI import DistributedLobbyAI
from game.cars.dungeon.DistributedDungeonAI import DistributedDungeonAI
from game.cars.lobby.DistributedTutorialLobbyContextAI import DistributedTutorialLobbyContextAI

class DistributedTutorialLobbyAI(DistributedLobbyAI):
    def __init__(self, air):
        DistributedLobbyAI.__init__(self, air)

    def join(self):
        print("join()")
        avatarId = self.air.getAvatarIdBySender()

        # Maybe host it's own context zone allocation?
        contextZoneId = self.air.allocateZone()
        zoneId = self.air.allocateZone()

        lobbyContext = DistributedTutorialLobbyContextAI(self.air)
        lobbyContext.owningAv = avatarId
        lobbyContext.playersInContext.append(avatarId)
        lobbyContext.generateOtpObject(self.doId, contextZoneId)

        dungeon = DistributedDungeonAI(self.air)
        dungeon.dungeonItemId = 1000 # New Player Tutorial from constants.js
        dungeon.playerIds.append(avatarId)
        dungeon.lobbyDoId = self.doId
        dungeon.contextDoId = lobbyContext.doId
        dungeon.generateWithRequired(zoneId)

        lobbyContext.b_setGotoDungeon(self.air.district.doId, dungeon.zoneId)
        self.sendUpdateToAvatarId(avatarId, 'gotoLobbyContext', [contextZoneId])
