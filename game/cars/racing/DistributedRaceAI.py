from typing import Dict, List
from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.showbase.PythonUtil import Functor

from game.cars.dungeon.DistributedDungeonAI import DistributedDungeonAI
from game.cars.carplayer.DistributedCarPlayerAI import DistributedCarPlayerAI
from .Track import Track
from .TrackSegment import TrackSegment
from .RaceGlobals import getRewardsForTrack
from direct.task.Task import Task

class DistributedRaceAI(DistributedDungeonAI):
    notify = directNotify.newCategory("DistributedRaceAI")
    COUNTDOWN_TIME = 4

    def __init__(self, air, track):
        DistributedDungeonAI.__init__(self, air)
        self.track: Track = track
        self.countDown: int = self.COUNTDOWN_TIME

        self.playerIdToLap: Dict[int, int] = {}
        self.playerIdToReady: Dict[int, bool] = {}
        self.playerIdToSegment: Dict[int, TrackSegment] = {}
        self.finishedPlayerIds: List[int] = []
        self.playerIdsThatLeft: List[int] = []

        self.totalRaceTime = 0
        self.playerIdToBestLapTime: Dict[int, int] = {}
        self.playerIdToCurrentLapTime: Dict[int, int] = {}
        self.playerIdToMaxLap: Dict[int, int] = {}

        self.playerIdInPhotoFinish: List[int] = []

        self.places: List[int] = [0, 0, 0, 0]

    def announceGenerate(self):
        for player in self.playerIds:
            self.playerIdToLap[player] = 1
            self.playerIdToMaxLap[player] = 1
            self.playerIdToBestLapTime[player] = 900000 # 15 minutes, seems like the best default.
            self.playerIdToReady[player] = False
            self.playerIdToSegment[player] = self.track.segmentById[self.track.startingTrackSegment]

            self.accept(self.staticGetZoneChangeEvent(player), Functor(self._playerChangedZone, player))
            self.acceptOnce(self.air.getDeleteDoIdEvent(player), self.playerDeleted, extraArgs=[player])

    def _playerChangedZone(self, playerId, newZoneId, oldZoneId):
        self.notify.debug(f"_playerChangedZone: {playerId} - {newZoneId} - {oldZoneId}")
        # Client seems to set their player's zone to the quiet zone
        # for all races, yet communicating with all of their opponents seem
        # to magically work, even when there are multiple racing running...
        if playerId in self.playerIds and oldZoneId == 1:
            self.playerDeleted(playerId)

    def playerDeleted(self, playerId):
        if playerId not in self.playerIds:
            return
        self.notify.debug(f"Player {playerId} have left the race!")
        self.playerIds.remove(playerId)
        self.playerIdsThatLeft.append(playerId)
        self.ignore(self.staticGetZoneChangeEvent(playerId))
        self.ignore(self.air.getDeleteDoIdEvent(playerId))

        taskMgr.remove(self.taskName(f"playerLapTime-{playerId}"))

        if playerId in self.playerIdToReady:
            del self.playerIdToReady[playerId]
            self.shouldStartRace()

        if not self.getActualPlayers():
            self.notify.debug("Everybody has left, shutting down...")
            self.requestDelete()

    def delete(self):
        # Stop the rest of the Tasks:
        taskMgr.remove(self.taskName("countDown"))
        taskMgr.remove(self.taskName("totalRaceTime"))
        taskMgr.remove(self.taskName("placeUpdate"))
        for playerId in self.playerIds:
            self.ignore(self.staticGetZoneChangeEvent(playerId))
            self.ignore(self.air.getDeleteDoIdEvent(playerId))
            taskMgr.remove(self.taskName(f"playerLapTime-{playerId}"))

        # Delete the lobby context if it still exists.
        context: DistributedObjectAI = self.air.getDo(self.contextDoId)
        if context:
            context.requestDelete()
        DistributedDungeonAI.delete(self)

    def getActualPlayers(self):
        return list(filter(lambda playerId: not self.isNPC(playerId), self.playerIds))

    def isNPC(self, playerId):
        # SPRaceAI overrides this.
        return False

    def sendPlaces(self):
        firstPlaceIndexToDetermine = 0
        numPlayersDidntFinish = 0

        self.places = [0, 0, 0, 0]

        # Players that have finished must retain their position and increment the first position we check for other players.
        for player in self.finishedPlayerIds:
            finishedPlaceIndex = self.finishedPlayerIds.index(player)
            self.places[3 - finishedPlaceIndex] = player
            firstPlaceIndexToDetermine += 1

        # Players that left but didn't finish will display as the lowest position based on the index (e.g. the first player that leaves would be 4th).
        for player in self.playerIdsThatLeft:
            # if player in self.finishedPlayerIds:
                continue

            # self.places[self.playerIdsThatLeft.index(player)] = player
            # numPlayersDidntFinish += 1

        # Now we need to store and churn through lap and segment data from players that are still in the race and haven't finished yet.
        playerLapsAndSegmentsIds: Dict[int, tuple] = {}

        for player in self.playerIds:
            if player in self.finishedPlayerIds:
                continue

            playerLap = self.playerIdToLap.get(player)
            playerSegment = self.playerIdToSegment.get(player)
            playerLapsAndSegmentsIds[player] = (playerLap, playerSegment.id)

        if len(playerLapsAndSegmentsIds) == 0:
            # All players have finished/left. Just send the update now.
            self.sendUpdate('setPlaces', [list(i for i in self.places if i != 0)])
            return

        playersOnFurthestLap: List[int] = []
        playersInFurthestSegment: List[int] = []

        for placeIndex in range(firstPlaceIndexToDetermine, (len(self.playerIds) - numPlayersDidntFinish)):
            # If we still have players to churn through on the furthest lap, we don't need to iterate again.
            if not playersOnFurthestLap:
                furthestLap = -1
                for player in playerLapsAndSegmentsIds:
                    playerLap, playerSegmentId = playerLapsAndSegmentsIds.get(player)
                    if not playersOnFurthestLap or playerLap > furthestLap:
                        furthestLap = playerLap
                        playersOnFurthestLap = [player]
                    elif playerLap == furthestLap:
                        playersOnFurthestLap.append(player)

            # Same as above, but for segment:
            if not playersInFurthestSegment:
                furthestSegmentId = -1
                for player in playersOnFurthestLap:
                    playerLap, playerSegmentId = playerLapsAndSegmentsIds.get(player)
                    if not playersInFurthestSegment or playerSegmentId > furthestSegmentId:
                        furthestSegmentId = playerSegmentId
                        playersInFurthestSegment = [player]
                    elif playerSegmentId == furthestSegmentId:
                        playersInFurthestSegment.append(player)

            # TODO: Determine what happens if there's a segment tie. Right now, lowest avId gets the lower place.
            playerForThisPlace = playersInFurthestSegment[0]
            self.places[3 - placeIndex] = playerForThisPlace

            # Cleanup for further iterations.
            del playerLapsAndSegmentsIds[playerForThisPlace]
            playersOnFurthestLap.remove(playerForThisPlace)
            playersInFurthestSegment.remove(playerForThisPlace)

        self.sendUpdate('setPlaces', [list(i for i in self.places if i != 0)])

    def raceStarted(self) -> bool:
        return self.countDown == 0

    def isEverybodyReady(self) -> bool:
        self.notify.debug(f"isEverybodyReady: {self.playerIdToReady}")
        return all(self.playerIdToReady.values())

    def syncReady(self):
        playerId = self.air.getAvatarIdFromSender()
        self.notify.debug(f"Player {playerId} is ready.")
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return
        self.playerIdToReady[playerId] = True

        self.shouldStartRace()

    def shouldStartRace(self):
        if self.raceStarted() or taskMgr.hasTaskNamed(self.taskName("countDown")):
            return

        if self.isEverybodyReady():
            self.notify.debug("Everybody ready, starting countdown.")
            # 0 so the countdown can start next frame
            self.doMethodLater(0, self.__doCountDown, self.taskName("countDown"))

    def onSegmentEnter(self, segment, fromSegment, forward):
        playerId = self.air.getAvatarIdFromSender()
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return
        self.handleSegmentEnter(playerId, segment, fromSegment, forward)

    def handleSegmentEnter(self, playerId, segment, fromSegment, forward):
        if not self.raceStarted():
            # The client send those messages early to set things up, ignore.
            self.notify.debug(f"Early handleSegmentEnter called for player {playerId}")
            return

        if playerId in self.finishedPlayerIds:
            return

        currentSegment = self.playerIdToSegment.get(playerId)
        if not currentSegment:
            self.notify.warning(f"Missing current segment for player {playerId}!")
            return

        self.notify.debug(f"handleSegmentEnter: {playerId} - {segment} - {currentSegment.id} - {forward}")

        if segment in currentSegment.childrenIds:
            childSegment = currentSegment.childrenById.get(segment)
            if not childSegment:
                self.notify.warning(f"Child segment {segment} does not exist from segment {currentSegment.id}")
                return
            self.playerIdToSegment[playerId] = childSegment
            if childSegment.id == self.track.startingTrackSegment:
                # It has reached a lap!
                self.playerIdToLap[playerId] += 1
                self.notify.debug(f"{playerId} has reached lap {self.playerIdToLap[playerId]}!")
                if self.playerIdToLap[playerId] > self.playerIdToMaxLap[playerId]:
                    self.playerIdToMaxLap[playerId] = self.playerIdToLap[playerId]
                    if self.playerIdToCurrentLapTime[playerId] < self.playerIdToBestLapTime[playerId]:
                        self.playerIdToBestLapTime[playerId] = self.playerIdToCurrentLapTime[playerId]
                    self.playerIdToCurrentLapTime[playerId] = 0
        elif segment in currentSegment.parentIds:
            parentSegment = currentSegment.parentById.get(segment)
            if not parentSegment:
                self.notify.warning(f"Parent segment {segment} does not exist from segment {currentSegment.id}")
                return
            self.playerIdToSegment[playerId] = parentSegment
            if parentSegment.id == self.track.startingTrackSegment:
                # They have reached back a lap!
                self.playerIdToLap[playerId] -= 1
                self.notify.debug(f"{playerId} went back to lap {self.playerIdToLap[playerId]}!")

        if self.playerIdToLap[playerId] > self.track.totalLaps:
            self.playerFinishedRace(playerId)

    def playerEnterPhotoFinish(self, playerId) -> bool:
        if playerId in self.playerIdInPhotoFinish:
            return False

        self.playerIdInPhotoFinish.append(playerId)
        return True

    def playerFinishedRace(self, playerId):
        if playerId in self.finishedPlayerIds:
            return

        self.notify.debug(f"{playerId} has finished the race!")
        self.finishedPlayerIds.append(playerId)

        place = self.finishedPlayerIds.index(playerId) + 1

        self.sendUpdate('setRacerResult', (playerId, place, self.playerIdToBestLapTime[playerId], self.totalRaceTime, playerId in self.playerIdInPhotoFinish, 0))

        if self.isNPC(playerId):
            # We don't give out rewards to NPCs.
            return

        player: DistributedCarPlayerAI = self.air.getDo(playerId)
        if not player:
            self.notify.warning(f"No player for playerid: {playerId}")
            return

        coins, racingPoints = getRewardsForTrack(self.track.name, place)
        player.addCoins(coins)
        flowPath = player.racecar.addRacingPoints(racingPoints)

        # See com.disney.cars.states.isoworld.ISOInstance
        player.d_invokeRuleResponse(0, [flowPath, place, racingPoints, coins], -self.dungeonItemId)

    def __doCountDown(self, task: Task):
        self.countDown -= 1
        self.sendUpdate('setCountDown', (self.countDown,))
        if self.countDown == 0:
            # Start the timers.
            taskMgr.add(self.__doTotalRaceTime, self.taskName("totalRaceTime"))
            for playerId in self.playerIds:
                taskMgr.add(self.__doPlayerLapTime, self.taskName(f"playerLapTime-{playerId}"), extraArgs=[playerId], appendTask=True)
            self.doMethodLater(1.0, self.__doPlaceUpdate, self.taskName("placeUpdate"))
            return task.done

        task.delayTime = 1
        return task.again

    def __doTotalRaceTime(self, task: Task):
        self.totalRaceTime = int(task.time * 1000)
        return task.cont

    def __doPlayerLapTime(self, playerId: int, task: Task):
        if playerId not in self.playerIds:
            return task.done
        self.playerIdToCurrentLapTime[playerId] = int(task.time * 1000)
        return task.cont

    def __doPlaceUpdate(self, task: Task):
        self.sendPlaces()
        return task.again
