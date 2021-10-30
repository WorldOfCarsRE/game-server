from .DistributedMinigameAI import DistributedMinigameAI

from . import CatchGameId

from typings import List

NumFruits = [

  # 1 player
  {2000: 18,
   1000: 19,
   5000: 22,
   4000: 24,
   3000: 27,
   9000: 28},

  # 2 player
  {2000: 30,
   1000: 33,
   5000: 38,
   4000: 42,
   3000: 46,
   9000: 50},

  # 3 players
  {2000: 42,
   1000: 48,
   5000: 54,
   4000: 60,
   3000: 66,
   9000: 71},

  # 4 players
  {2000: 56
   1000: 63,
   5000: 70,
   4000: 78,
   3000: 85,
   9000: 92},

]

class DistributedCatchGameAI(DistributedMinigameAI):
    MINIGAME_ID = CatchGameId
    DURATION = 55

    def __init__(self, air, participants, trolleyZone):
        DistributedMinigameAI.__init__(self, air, participants, trolleyZone)
        self.numFruits: List[] = []
        self.fruitsCaught: int = 0

    def onGameStart(self):
        taskMgr.doMethodLater(self.DURATION, self.gamesOver, self.uniqueName('timer'))

    def hasGameBegun(self):
        return self.state == 'GameBegin'

    def claimCatch(self, objNum, objTypeId):
        if not self.hasGameBegun():
            return

    def reportDone(self):
        if not self.hasGameBegun():
            return
        avId = self.air.currentAvatarSender

    def exitGameBegin(self):
        taskMgr.remove(self.uniqueName('timer'))

    def gamesOver(self, task = None):
        self.demand('Cleanup')