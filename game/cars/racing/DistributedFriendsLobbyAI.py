from game.cars.racing.DistributedLobbyAI import DistributedLobbyAI

from .Track import Track

class DistributedFriendsLobbyAI(DistributedLobbyAI):
    def __init__(self, air, hotSpotName, dungeonItemId, track):
        DistributedLobbyAI.__init__(self, air)

        self.hotSpotName: str = hotSpotName
        self.dungeonItemId: int = dungeonItemId
        self.track: Track = Track(hotSpotName, track)
        self.track.totalLaps = 3
