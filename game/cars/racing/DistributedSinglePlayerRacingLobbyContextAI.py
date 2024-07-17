from game.cars.lobby.DistributedLobbyContextAI import DistributedLobbyContextAI

class DistributedSinglePlayerRacingLobbyContextAI(DistributedLobbyContextAI):
    def __init__(self, air):
        DistributedLobbyContextAI.__init__(self, air)
