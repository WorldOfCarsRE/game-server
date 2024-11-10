from game.cars.lobby.DistributedLobbyContextAI import DistributedLobbyContextAI

class DistributedCrossShardLobbyContextAI(DistributedLobbyContextAI):
    def __init__(self, air):
        DistributedLobbyContextAI.__init__(self, air)
        self.timeLeft = -1

    def getTimeLeft(self):
        return self.timeLeft
