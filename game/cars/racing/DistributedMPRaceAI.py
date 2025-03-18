from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.task.Task import Task

from .DistributedRaceAI import DistributedRaceAI

from game.cars.carplayer.racing.HazardAI import HazardAI

from collections import Counter
from copy import copy

HAZARD_HAY_BALE_BOMB_ITEM = 502
HAZARD_SMOKE_SCREEN_ITEM = 503

class DistributedMPRaceAI(DistributedRaceAI):
    notify = directNotify.newCategory("DistributedMPRaceAI")
    notify.setDebug(1)

    def __init__(self, air, track):
        DistributedRaceAI.__init__(self, air, track)
        self.waitForPlayers = []
        self.playersQuit: list[int] = []
        self.playersRacing: list[int] = []
        self.playersRaceSummary: list[int] = []
        self.playersAvailable: list[int] = []
        self.playersReady: list[int] = []
        self.playerSpeeds: dict[int, tuple[int, int]] = {}

        self.gearingUp = False
        self.timer = 31
        self.playersGearedUp: list[int] = []

    def delete(self):
        # Stop multiplayer specific tasks.
        taskMgr.remove(self.taskName("gearUpCountdown"))

        DistributedRaceAI.delete(self)

    def getWaitForObjects(self):
        return self.waitForPlayers

    def shouldStartRace(self):
        DistributedRaceAI.shouldStartRace(self)
        if self.isEverybodyReady():
            self.playersRacing = self.playerIds[:]

    def dropHazard(self, x, y, itemId):
        playerId = self.air.getAvatarIdFromSender()
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return
        
        hazard = HazardAI(self.air)

        if itemId == HAZARD_HAY_BALE_BOMB_ITEM:
            hazard.assetId = 5002
            hazard.clientScript = "scripts/interactive/racing_hazard_hayBaleBomb.lua"
        elif itemId == HAZARD_SMOKE_SCREEN_ITEM:
            hazard.assetId = 5003
            hazard.clientScript = "scripts/interactive/racing_hazard_smokeScreen.lua"

        hazard.x, hazard.y = x, y
        hazard.generateWithRequired(self.zoneId)

        self.interactiveObjects.append(hazard)

    def setQuit(self):
        playerId = self.air.getAvatarIdFromSender()
        self.notify.debug(f"setQuit: {playerId}")
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return
        if playerId in self.playersQuit:
            return

        self.sendUpdate("setPlayerQuit", (playerId,))
        self.playersQuit.append(playerId)

    def playerDeleted(self, playerId):
        if playerId not in self.playersQuit:
            self.sendUpdate("setPlayerQuit", (playerId,))
            self.playersQuit.append(playerId)

        if playerId in self.waitForPlayers:
            self.waitForPlayers.remove(playerId)
            self.sendUpdate("waitForObjects", (self.waitForPlayers,))

        if playerId in self.playersRacing:
            self.playersRacing.remove(playerId)
        if playerId in self.playersRaceSummary:
            self.playersRaceSummary.remove(playerId)
        if playerId in self.playersReady:
            self.playersReady.remove(playerId)
        if playerId in self.playersGearedUp:
            self.playersGearedUp.remove(playerId)

        DistributedRaceAI.playerDeleted(self, playerId)

        if len(self.getRemainingPlayers()) > 1:
            self.shouldStartGearUp()

    def handleSegmentEnter(self, playerId, segment, fromSegment, forward):
        DistributedRaceAI.handleSegmentEnter(self, playerId, segment, fromSegment, forward)

        if playerId in self.finishedPlayerIds:
            return

        currentSegment = self.playerIdToSegment.get(playerId)
        if not currentSegment:
            return

        if self.playerIdToLap.get(playerId) != self.track.totalLaps:
            return

        if self.track.startingTrackSegment in currentSegment.childrenById:
            # This player is about to finish, check for other players for
            # photo finish.
            for otherPlayerId in self.playerIds:
                if otherPlayerId == playerId:
                    continue
                if self.playerIdToSegment.get(otherPlayerId) is currentSegment and \
                    self.playerIdToLap.get(otherPlayerId) == self.track.totalLaps:
                    if self.playerEnterPhotoFinish(playerId):
                        self.sendUpdateToAvatarId(playerId, "startPhotoFinish", ())
                    if self.playerEnterPhotoFinish(otherPlayerId):
                        self.sendUpdateToAvatarId(otherPlayerId, "startPhotoFinish", ())

    def broadcastSpeeds(self, topSpeed, averageSpeed):
        playerId = self.air.getAvatarIdFromSender()
        self.notify.debug(f"broadcastSpeeds: {playerId}, {topSpeed}, {averageSpeed}")
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return

        self.playerSpeeds[playerId] = (topSpeed, averageSpeed)

    def playerFinishedRace(self, playerId):
        DistributedRaceAI.playerFinishedRace(self, playerId)

        for item in self.playerSpeeds.items():
            speedPlayerId = item[0]
            topSpeed, averageSpeed = item[1]
            self.sendUpdate("setSpeeds", (speedPlayerId, topSpeed, averageSpeed))

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

        self.shouldStartGearUp()

    def getRemainingPlayers(self) -> list:
        return [player for player in self.playerIds if player not in self.playersQuit]

    def shouldStartGearUp(self):
        if not self.gearingUp and Counter(self.playerIds) == Counter(self.playersReady):
            self.notify.debug("Everybody's ready, starting gear up...")
            self.sendUpdate("startGearUp", ())
            self.gearingUp = True

            self.doMethodLater(0, self.__doGearupCountdown, self.taskName("gearUpCountdown"))

    def setGearedUp(self):
        playerId = self.air.getAvatarIdFromSender()
        self.notify.debug(f"setGearedUp: {playerId}")
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return
        if not self.gearingUp:
            self.notify.warning(f"{playerId} attempted to gear up even though we're not gearing up!")
            return
        if playerId in self.playersGearedUp:
            return
        if len(self.getRemainingPlayers()) < 2:
            return

        self.sendUpdate('setPlayerReady', (playerId,))
        self.playersGearedUp.append(playerId)

        self.sendUpdateToAvatarId(playerId, "setTimeLeft", (self.timer,))

        if Counter(self.playerIds) == Counter(self.playersGearedUp):
            # Restart timer
            self.timer = 6
            taskMgr.remove(self.taskName("gearUpCountdown"))
            self.doMethodLater(0, self.__doGearupCountdown, self.taskName("gearUpCountdown"))

    def __doGearupCountdown(self, task: Task):
        if len(self.getRemainingPlayers()) < 2:
            # Only one player is left, no point doing another race.
            return task.done
        self.timer -= 1
        self.sendUpdate("setTimeLeft", (self.timer,))

        if Counter(self.playerIds) != Counter(self.playersGearedUp):
            self.sendUpdate("setGearUpTimeLeft", (self.timer,))

        if self.timer == 0:
            if len(self.getRemainingPlayers()) > 1:
                # Generate new race:
                zoneId = self.air.allocateZone()
                race = DistributedMPRaceAI(simbase.air, self.track)
                race.playerIds = self.playerIds[:]
                race.waitForPlayers = self.playerIds[:]
                race.lobbyDoId = copy(self.lobbyDoId)
                race.contextDoId = copy(self.contextDoId)
                race.dungeonItemId = copy(self.dungeonItemId)
                race.generateWithRequired(zoneId)

                self.sendUpdate("gotoDungeon", (simbase.air.district.doId, zoneId))

                # Delete this old race.
                race.contextDoId = 0
                self.requestDelete()
            return task.done

        task.delayTime = 1
        return task.again
