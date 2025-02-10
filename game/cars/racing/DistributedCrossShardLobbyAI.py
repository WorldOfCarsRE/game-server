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

    def join(self):
        avatarId = self.air.getAvatarIdFromSender()

        # TODO: Check with other shards, might require a UD and use NetMessenger.

        activeContext: DistributedCrossShardLobbyContextAI = None
        for context in self.contexts:
            if context.isAcceptingNewPlayers():
                activeContext = context
                context.addPlayerInContext(avatarId)
                break
        
        if not activeContext:
            # Maybe host it's own context zone allocation?
            contextZoneId = self.air.allocateZone()
            activeContext = DistributedCrossShardLobbyContextAI(self.air)
            activeContext.lobby = self
            activeContext.addPlayerInContext(avatarId)
            activeContext.generateOtpObject(self.doId, contextZoneId)
            self.contexts.append(activeContext)

        self.sendUpdateToAvatarId(avatarId, 'gotoLobbyContext', [activeContext.zoneId])

    def quit(self):
        avatarId = self.air.getAvatarIdFromSender()
        for context in self.contexts:
            if avatarId in context.playersInContext:
                context.removePlayerInContext(avatarId)
                break
