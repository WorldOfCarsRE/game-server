from game.cars.racing.DistributedLobbyAI import DistributedLobbyAI
from game.cars.racing.DistributedSinglePlayerRacingLobbyContextAI import DistributedSinglePlayerRacingLobbyContextAI
from game.cars.racing.DistributedSPRaceAI import DistributedSPRaceAI
from game.cars.distributed.CarsGlobals import DUNGEON_INTEREST_HANDLE

from .Track import Track

class DistributedSinglePlayerRacingLobbyAI(DistributedLobbyAI):

    def __init__(self, air, hotSpotName, dungeonItemId, track):
        DistributedLobbyAI.__init__(self, air)

        self.hotSpotName: str = hotSpotName
        self.dungeonItemId: int = dungeonItemId
        self.track: Track = Track(hotSpotName, track)
        self.track.totalLaps = 3

    def join(self):
        avatarId = self.air.getAvatarIdFromSender()

        # Maybe host it's own context zone allocation?
        contextZoneId = self.air.allocateZone()
        zoneId = self.air.allocateZone()

        lobbyContext = DistributedSinglePlayerRacingLobbyContextAI(self.air)
        lobbyContext.lobby = self
        lobbyContext.playersInContext.append(avatarId)
        lobbyContext.generateOtpObject(self.doId, contextZoneId)

        race = DistributedSPRaceAI(self.air, self.track)
        race.playerIds.append(avatarId)
        race.lobbyDoId = self.doId
        race.contextDoId = lobbyContext.doId
        race.dungeonItemId = self.dungeonItemId
        race.generateWithRequired(zoneId)

        lobbyContext.b_setGotoDungeon(self.air.district.doId, race.zoneId)
        self.sendUpdateToAvatarId(avatarId, 'gotoLobbyContext', [contextZoneId])
