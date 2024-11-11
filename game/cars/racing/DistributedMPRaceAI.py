from direct.directnotify.DirectNotifyGlobal import directNotify

from .DistributedRaceAI import DistributedRaceAI

class DistributedMPRaceAI(DistributedRaceAI):
    notify = directNotify.newCategory("DistributedMPRaceAI")

    def __init__(self, air, track):
        DistributedRaceAI.__init__(self, air, track)
        self.playersRacing: list[int] = []
        self.playersRaceSummary: list[int] = []
        self.playersAvailable: list[int] = []
        self.playersReady: list[int] = []
        self.playerSpeeds: dict[int, tuple[int, int]] = {}

    def getWaitForObjects(self):
        return self.playerIds

    def shouldStartRace(self):
        DistributedRaceAI.shouldStartRace(self)
        if self.isEverybodyReady():
            self.playersRacing = self.playerIds[:]

    def dropHazard(self, x, y, itemId):
        playerId = self.air.getAvatarIdFromSender()
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return
        self.notify.warning(f"TODO: dropHazard - {x}, {y}, {itemId}")

    def setQuit(self):
        playerId = self.air.getAvatarIdFromSender()
        self.notify.debug(f"setQuit: {playerId}")
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return
        self.playerDeleted(playerId)

    def playerDeleted(self, playerId):
        self.sendUpdate("setPlayerQuit", (playerId,))
        DistributedRaceAI.playerDeleted(self, playerId)

    def broadcastSpeeds(self, topSpeed, averageSpeed):
        playerId = self.air.getAvatarIdFromSender()
        self.notify.debug(f"broadcastSpeeds: {playerId}, {topSpeed}, {averageSpeed}")
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return

        self.playerSpeeds[playerId] = (topSpeed, averageSpeed)

    def playerFinishedRace(self, playerId):
        DistributedRaceAI.playerFinishedRace(self, playerId)

        topSpeed, averageSpeed = self.playerSpeeds.get(playerId, (0, 0))
        self.sendUpdate("setSpeeds", (playerId, topSpeed, averageSpeed))

        if self.playersRacing:
            self.sendUpdateToAvatarId(playerId, 'setPlayersRacing', (self.playersRacing,))
        if self.playersRaceSummary:
            self.sendUpdateToAvatarId(playerId, "setPlayersRaceSummary", (self.playersRaceSummary,))
        if self.playersAvailable:
            self.sendUpdateToAvatarId(playerId, "setPlayersAvailable", (self.playersAvailable,))
        if self.playersReady:
            self.sendUpdateToAvatarId(playerId, "setPlayersReady", (self.playersReady,))

    def setRaceSummary(self):
        playerId = self.air.getAvatarIdFromSender()
        self.notify.debug(f"setRaceSummary: {playerId}")
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return
        if playerId in self.playersRaceSummary:
            return
        self.playersRaceSummary.append(playerId)
        self.sendUpdate("setPlayerRaceSummary", (playerId,))

        if playerId in self.playersRacing:
            self.playersRacing.remove(playerId)

    def setAvailable(self):
        playerId = self.air.getAvatarIdFromSender()
        self.notify.debug(f"setAvailable: {playerId}")
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return
        if playerId in self.playersAvailable:
            return
        self.playersAvailable.append(playerId)
        self.sendUpdate("setPlayerAvailable", (playerId,))

        if playerId in self.playersRacing:
            self.playersRacing.remove(playerId)

        if playerId in self.playersRaceSummary:
            self.playersRaceSummary.remove(playerId)

    def setReady(self):
        playerId = self.air.getAvatarIdFromSender()
        self.notify.debug(f"setReady: {playerId}")
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return
        if playerId in self.playersReady:
            return
        self.playersReady.append(playerId)
        self.sendUpdate("setPlayerReady", (playerId,))

        if playerId in self.playersRacing:
            self.playersRacing.remove(playerId)

        if playerId in self.playersRaceSummary:
            self.playersRaceSummary.remove(playerId)

        if playerId in self.playersAvailable:
            self.playersAvailable.remove(playerId)

    def setGearedUp(self):
        playerId = self.air.getAvatarIdFromSender()
        self.notify.warning(f"TODO: setGearedUp - ${playerId}")
