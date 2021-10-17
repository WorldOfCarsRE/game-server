from .DistributedMinigameAI import DistributedMinigameAI

from . import RingGameId

import random

from typing import List, Dict, Tuple

class RingGameGlobals:
    NUM_RING_GROUPS = 16
    RING_COLOR_SELECTION = [(0, 1, 2), 3, 4, 5, 6]

class DistributedRingGameAI(DistributedMinigameAI):
    MINIGAME_ID = RingGameId
    DURATION = 60

    def __init__(self, air, participants, trolleyZone):
        DistributedMinigameAI.__init__(self, air, participants, trolleyZone)
        self.colors: List[int] = [-1] * len(participants)
        self.__nextRingGroup: Tuple[int] = {}
        self.__numRingsPassed: List[int] = [0] * RingGameGlobals.NUM_RING_GROUPS
        self.__ringResultBitfield: List[int] = [0] * RingGameGlobals.NUM_RING_GROUPS
        self.failedOnce: List[int] = []
        
        self.setTimeBase(globalClockDelta.localToNetworkTime(globalClock.getRealTime()))
        self.selectColorIndices()
            
    def setTimeBase(self, timeBase):
        self.__timeBase = timeBase

    def getTimeBase(self):
        return self.__timeBase
        
    def selectColorIndices(self):
        colorIndices = [None, None, None, None]
        chooseFrom = RingGameGlobals.RING_COLOR_SELECTION[:]
        for color in range(0, 4):
            c = random.choice(chooseFrom)
            chooseFrom.remove(c)
            if isinstance(c, tuple):
                c = random.choice(c)
            colorIndices[color] = c
        self.setColorIndices(colorIndices)
        
    def setColorIndices(self, colorIndices):
        self.colorIndices = colorIndices
        
    def getColorIndices(self):
        return self.colorIndices[0], self.colorIndices[1], self.colorIndices[2], self.colorIndices[3]

    def onGameStart(self):
        taskMgr.doMethodLater(self.DURATION, self.gamesOver, self.uniqueName('timer'))
        
    def setToonGotRing(self, success):
        senderId = self.air.currentAvatarSender

        sender = self.air.doTable[senderId]
        if not sender:
            return
            
        if senderId not in self.__nextRingGroup:
            self.__nextRingGroup[senderId] = 0
            
        ringGroupIndex = self.__nextRingGroup[senderId]
        if ringGroupIndex >= RingGameGlobals.NUM_RING_GROUPS:
            return
        
        self.__nextRingGroup[senderId] += 1
        
        if success:
            if senderId in self.scoreDict:
                self.scoreDict[senderId] += 1
            else:
                self.scoreDict[senderId] = 1
        else:
            self.__ringResultBitfield[ringGroupIndex] |= 1 << self.participants.index(senderId)
            if senderId not in self.failedOnce:
                self.failedOnce.append(senderId)
                
        self.__numRingsPassed[ringGroupIndex] += 1
        if self.__numRingsPassed[ringGroupIndex] >= self.getNumParticipants():
            if not self.isSinglePlayer():
                bitfield = self.__ringResultBitfield[ringGroupIndex]
                if bitfield == 0x00:
                    for participant in self.getParticipants():
                        if participant in self.scoreDict:
                            self.scoreDict[participant] += .5

                self.sendUpdate('setRingGroupResults', [bitfield])
                
            if ringGroupIndex >= (RingGameGlobals.NUM_RING_GROUPS-1):
                perfectBonuses = {
                  1 : 5,
                  2 : 5,
                  3 : 10,
                  4 : 18,
                }
                numPerfectParticipants = 0
                for participant in self.getParticipants():
                    if participant not in self.failedOnce:
                        numPerfectParticipants += 1
                
                for participant in self.getParticipants():
                    if participant not in self.scoreDict:
                        return
                    if participant not in self.failedOnce:
                        self.scoreDict[participant] += perfectBonuses[numPerfectParticipants]
                    if self.scoreDict[participant] < 1:
                        self.scoreDict[participant] = 1
                        
                self.gamesOver()

    def exitGameBegin(self):
        taskMgr.remove(self.uniqueName('timer'))

    def gamesOver(self, task=None):
        self.demand('Cleanup')

