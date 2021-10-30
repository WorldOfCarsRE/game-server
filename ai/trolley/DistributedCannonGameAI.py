from .DistributedMinigameAI import DistributedMinigameAI

from . import CannonGameId

TowerYRange = 200

MAX_SCORE = 23
MIN_SCORE = 5

FUSE_TIME = 0

CANNON_ROTATION_MIN = -20
CANNON_ROTATION_MAX = 20
CANNON_ROTATION_VEL = 15.0

CANNON_ANGLE_MIN = 10
CANNON_ANGLE_MAX = 85
CANNON_ANGLE_VEL = 15.0

def calcScore(t, gameTime):
    range = MAX_SCORE - MIN_SCORE
    score = MAX_SCORE - (range * (float(t) / gameTime))
    return int(score + .5)

class DistributedCannonGameAI(DistributedMinigameAI):
    MINIGAME_ID = CannonGameId
    DURATION = 90

    def __init__(self, air, participants, trolleyZone):
        DistributedMinigameAI.__init__(self, air, participants, trolleyZone)

    def onGameStart(self):
        taskMgr.doMethodLater(self.DURATION, self.gamesOver, self.uniqueName('timer'))

    def hasGameBegun(self):
        return self.state == 'GameBegin'

    def _checkCannonRange(self, zRot, angle, avId):
        outOfRange = 0
        if zRot < CANNON_ROTATION_MIN or zRot > CANNON_ROTATION_MAX:
            outOfRange = 1
        if angle < CANNON_ANGLE_MIN or angle > CANNON_ANGLE_MAX:
            outOfRange = 1
        return outOfRange

    def setCannonPosition(self, zRot, angle):
        if not self.hasGameBegun():
            return
        avId = self.air.currentAvatarSender
        if self._checkCannonRange(zRot, angle, avId):
            return
        self.sendUpdate('updateCannonPosition', [avId, zRot, angle])

    def setCannonLit(self, zRot, angle):
        if not self.hasGameBegun():
            return
        avId = self.air.currentAvatarSender
        if self._checkCannonRange(zRot, angle, avId):
            return
        fireTime = self.getCurrentGameTime() + FUSE_TIME
        self.sendUpdate('setCannonWillFire', [avId, fireTime, zRot, angle])

    def setToonWillLandInWater(self, landTime):
        if not self.hasGameBegun():
            return
        senderAvId = self.air.currentAvatarSender
        score = calcScore(landTime, self.DURATION)
        for avId in self.participants:
            self.scoreDict[avId] = score

        taskMgr.remove(self.uniqueName('timer'))
        delay = landTime - self.getCurrentGameTime()
        if delay < 0:
            delay = 0
        taskMgr.doMethodLater(delay, self.toonLandedInWater, self.uniqueName('game-over'))
        self.sendUpdate('announceToonWillLandInWater', [senderAvId, landTime])

    def toonLandedInWater(self, task):
        if self.hasGameBegun():
            self.gamesOver()
        return task.done

    def exitGameBegin(self):
        taskMgr.remove(self.uniqueName('timer'))
        taskMgr.remove(self.uniqueName('game-over'))

    def gamesOver(self, task=None):
        self.demand('Cleanup')