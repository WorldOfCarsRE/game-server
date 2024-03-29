from ai.racing.DistributedLobbyAI import DistributedLobbyAI
from ai.racing.DistributedSinglePlayerRacingLobbyContextAI import DistributedSinglePlayerRacingLobbyContextAI
from ai.dungeon.DistributedSPRaceAI import DistributedSPRaceAI
from otp.constants import DUNGEON_INTEREST_HANDLE

class DistributedSinglePlayerRacingLobbyAI(DistributedLobbyAI):

    def __init__(self, air):
        DistributedLobbyAI.__init__(self, air)

        self.hotSpotName: str = 'spRace_ccs'
        self.dungeonItemId: int = 42001 # spRace_ccs

    def join(self):
        avatarId = self.air.currentAvatarSender

        zoneId = self.air.allocateZone()

        lobbyContext = DistributedSinglePlayerRacingLobbyContextAI(self.air)
        lobbyContext.owningAv = avatarId
        lobbyContext.playersInContext.append(avatarId)
        self.air.generateWithRequired(lobbyContext, DUNGEON_INTEREST_HANDLE, zoneId)

        race = DistributedSPRaceAI(self.air)
        race.playerIds.append(avatarId)
        race.lobbyDoId = self.doId
        race.contextDoId = lobbyContext.doId
        race.dungeonItemId = self.dungeonItemId
        self.air.generateWithRequired(race, self.doId, zoneId)

        self.sendUpdateToAvatar(avatarId, 'gotoLobbyContext', [zoneId])

        lobbyContext.b_setGotoDungeon(self.air.district.doId, race.zoneId)
