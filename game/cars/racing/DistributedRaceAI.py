
from typing import Dict, List
from direct.directnotify.DirectNotifyGlobal import directNotify

from game.cars.dungeon.DistributedDungeonAI import DistributedDungeonAI
from game.cars.carplayer.DistributedCarPlayerAI import DistributedCarPlayerAI
from .Track import Track
from .TrackSegment import TrackSegment
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

        self.places: List[int] = [0, 0, 0, 0]

    def announceGenerate(self):
        for player in self.playerIds:
            self.playerIdToLap[player] = 1
            self.playerIdToReady[player] = False
            self.playerIdToSegment[player] = self.track.segmentById[self.track.startingTrackSegment]

    def isNPC(self, playerId):
        return False

    def sendPlaces(self):
        # TODO
        pass

    def raceStarted(self) -> bool:
        return self.countDown == 0

    def isEverybodyReady(self) -> bool:
        if len(self.playerIds) == 4 and all(self.playerIdToReady.values()):
            return True
        return False

    def syncReady(self):
        playerId = self.air.getAvatarIdFromSender()
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return
        self.playerIdToReady[playerId] = True

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

        self.sendPlaces()
        if self.playerIdToLap[playerId] > self.track.totalLaps:
            self.playerFinishedRace(playerId)

    def playerFinishedRace(self, playerId):
        if playerId in self.finishedPlayerIds:
            return

        self.notify.debug(f"{playerId} has finished the race!")
        self.finishedPlayerIds.append(playerId)

        place = self.finishedPlayerIds.index(playerId) + 1

        # TODO: Times and photo finish?
        self.sendUpdate('setRacerResult', (playerId, place, 0, 0, 0, 0))

        if self.isNPC(playerId):
            # We don't give out rewards to NPCs.
            return

        player: DistributedCarPlayerAI = self.air.getDo(playerId)
        if not player:
            self.notify.warning(f"No player for playerid: {playerId}")
            return

        # TODO: Figure out and actually give out rewards.

        # See com.disney.cars.states.isoworld.ISOInstance
        player.d_invokeRuleResponse(0, [1, place, 0, 0], -self.dungeonItemId)

    def __doCountDown(self, task: Task):
        self.countDown -= 1
        self.sendUpdate('setCountDown', (self.countDown,))
        if self.countDown == 0:
            return task.done

        task.delayTime = 1
        return task.again
