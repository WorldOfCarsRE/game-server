from game.cars.lobby.DistributedLobbyAI import DistributedLobbyAI
from game.cars.dungeon.DistributedDungeonAI import DistributedDungeonAI
from game.cars.lobby.DistributedTutorialLobbyContextAI import DistributedTutorialLobbyContextAI
from game.cars.carplayer.npcs.TutorialTruckAI import TutorialTruckAI
from game.cars.distributed.CarsGlobals import DEFAULT_DUNGEON_ZONE

class DistributedTutorialLobbyAI(DistributedLobbyAI):
    def __init__(self, air):
        DistributedLobbyAI.__init__(self, air)

    def join(self):
        avatarId = self.air.getAvatarIdFromSender()

        # Maybe host it's own context zone allocation?
        contextZoneId = self.air.allocateZone()
        zoneId = self.air.allocateZone()

        lobbyContext = DistributedTutorialLobbyContextAI(self.air)
        lobbyContext.lobby = self
        lobbyContext.playersInContext.append(avatarId)
        lobbyContext.generateOtpObject(self.doId, contextZoneId)

        dungeon = DistributedDungeonAI(self.air)
        dungeon.dungeonItemId = 1000 # New Player Tutorial from constants.js
        dungeon.playerIds.append(avatarId)
        dungeon.lobbyDoId = self.doId
        dungeon.contextDoId = lobbyContext.doId
        dungeon.generateWithRequired(zoneId)

        truck = TutorialTruckAI(self.air)
        truck.generateOtpObject(dungeon.doId, DEFAULT_DUNGEON_ZONE)

        lobbyContext.b_setGotoDungeon(self.air.district.doId, dungeon.zoneId)
        self.sendUpdateToAvatarId(avatarId, 'gotoLobbyContext', [contextZoneId])
