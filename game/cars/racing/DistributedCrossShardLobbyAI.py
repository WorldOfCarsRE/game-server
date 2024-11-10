from game.cars.racing.DistributedLobbyAI import DistributedLobbyAI
from game.cars.racing.DistributedCrossShardLobbyContextAI import DistributedCrossShardLobbyContextAI

from .Track import Track


class DistributedCrossShardLobbyAI(DistributedLobbyAI):
    def __init__(self, air, hotSpotName, dungeonItemId, track):
        DistributedLobbyAI.__init__(self, air)

        self.hotSpotName: str = hotSpotName
        self.dungeonItemId: int = dungeonItemId
        self.track: Track = Track(hotSpotName, track)
        self.track.totalLaps = 3

        self.contexts: list[DistributedCrossShardLobbyContextAI] = []
        self.activeContext: DistributedCrossShardLobbyContextAI = None

    def join(self):
        avatarId = self.air.getAvatarIdFromSender()

        # TODO: Check with other shards, might require a UD and use NetMessenger.

        if self.activeContext:
            if self.activeContext.isAcceptingNewPlayers():
                self.activeContext.addPlayerInContext(avatarId)
        else:
            # Maybe host it's own context zone allocation?
            contextZoneId = self.air.allocateZone()
            self.activeContext = DistributedCrossShardLobbyContextAI(self.air)
            self.activeContext.lobby = self
            self.activeContext.playersInContext.append(avatarId)
            self.activeContext.generateOtpObject(self.doId, contextZoneId)
            self.contexts.append(self.activeContext)

        self.sendUpdateToAvatarId(avatarId, 'gotoLobbyContext', [self.activeContext.zoneId])

    def quit(self):
        avatarId = self.air.getAvatarIdFromSender()
        print(f"TODO: quit: {avatarId}")
