from typing import List
from direct.directnotify.DirectNotifyGlobal import directNotify

from .DistributedRaceAI import DistributedRaceAI

class DistributedSPRaceAI(DistributedRaceAI):
    notify = directNotify.newCategory("DistributedSPRaceAI")

    def __init__(self, air, track):
        DistributedRaceAI.__init__(self, air, track)
        self.npcPlayers: List[int] = []

    def setOpponentNPCs(self, npcPlayers: List[int]):
        if bool(self.npcPlayers):
            self.notify.warning("Attempted to send NPC list again!")
            return

        self.npcPlayers = npcPlayers

        for player in npcPlayers:
            self.playerIds.append(player)
            self.playerIdToLap[player] = 1
            self.playerIdToMaxLap[player] = 1
            self.playerIdToBestLapTime[player] = 900000 # 15 minutes, seems like the best default.
            self.playerIdToReady[player] = True
            self.playerIdToSegment[player] = self.track.segmentById[self.track.startingTrackSegment]

        self.shouldStartRace()

    def onNpcSegmentEnter(self, npcId, segment, fromSegment, forward):
        if npcId not in self.npcPlayers:
            self.notify.warning(f"Attempted to call onNpcSegmentEnter with an non-NPC player {npcId}!")
            return

        self.handleSegmentEnter(npcId, segment, fromSegment, forward)

    def isNPC(self, playerId):
        return playerId in self.npcPlayers
