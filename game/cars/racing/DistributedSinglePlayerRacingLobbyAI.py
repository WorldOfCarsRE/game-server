from game.cars.racing.DistributedLobbyAI import DistributedLobbyAI
from game.cars.racing.DistributedSinglePlayerRacingLobbyContextAI import DistributedSinglePlayerRacingLobbyContextAI
from game.cars.racing.DistributedSPRaceAI import DistributedSPRaceAI
from game.cars.distributed.CarsGlobals import DUNGEON_INTEREST_HANDLE

from .Track import Track

class DistributedSinglePlayerRacingLobbyAI(DistributedLobbyAI):

    def __init__(self, air):
        DistributedLobbyAI.__init__(self, air)

        # FIXME: Carburetor County race track doesn't seem to load at the moment,
        # for now we will use another map for experimenting.
        self.hotSpotName: str = 'spRace_ccs'
        self.dungeonItemId: int = 42001 # spRace_ccs
        self.track: Track = Track('car_w_trk_tfn_twistinTailfin_SS_V1_phys.xml')

    def join(self):
        avatarId = self.air.getAvatarIdFromSender()

        zoneId = self.air.allocateZone()

        lobbyContext = DistributedSinglePlayerRacingLobbyContextAI(self.air)
        lobbyContext.owningAv = avatarId
        lobbyContext.playersInContext.append(avatarId)
        lobbyContext.generateWithRequired(zoneId)

        race = DistributedSPRaceAI(self.air, self.track)
        race.playerIds.append(avatarId)
        race.lobbyDoId = self.doId
        race.contextDoId = lobbyContext.doId
        race.dungeonItemId = self.dungeonItemId
        race.generateWithRequired(DUNGEON_INTEREST_HANDLE)

        self.sendUpdateToAvatarId(avatarId, 'gotoLobbyContext', [zoneId])

        lobbyContext.b_setGotoDungeon(self.air.district.doId, race.zoneId)
