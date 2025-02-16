from game.cars.lobby.DistributedLobbyContextAI import DistributedLobbyContextAI

from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.task.Task import Task

from .DistributedMPRaceAI import DistributedMPRaceAI

class DistributedCrossShardLobbyContextAI(DistributedLobbyContextAI):
    notify = directNotify.newCategory("DistributedCrossShardLobbyContextAI")

    def __init__(self, air):
        DistributedLobbyContextAI.__init__(self, air)
        self.timeLeft = -1

    def getTimeLeft(self):
        return self.timeLeft

    def addPlayerInContext(self, avId):
        DistributedLobbyContextAI.addPlayerInContext(self, avId)
        if len(self.playersInContext) > 1 and not taskMgr.hasTaskNamed(self.taskName("countDown")):
            self.notify.debug("Starting countdown...")
            self.timeLeft = 11
            self.doMethodLater(0, self.__doCountDown, self.taskName("countDown"))

    def removePlayerInContext(self, avId):
        DistributedLobbyContextAI.removePlayerInContext(self, avId)
        if len(self.playersInContext) < 2 and taskMgr.hasTaskNamed(self.taskName("countDown")):
            self.notify.debug("Stopping countdown...")
            self.timeLeft = 11
            taskMgr.remove(self.taskName("countDown"))

    def __doCountDown(self, task: Task):
        self.timeLeft -= 1
        self.sendUpdate("setTimeLeft", (self.timeLeft,))
        if self.timeLeft == 0:
            self.playersInDungeon = self.playersInContext

            zoneId = self.air.allocateZone()
            race = DistributedMPRaceAI(self.air, self.lobby.track)
            race.playerIds = self.playersInContext[:]
            race.waitForPlayers = self.playersInContext[:]
            race.lobbyDoId = self.lobby.doId
            race.contextDoId = self.doId
            race.dungeonItemId = self.lobby.dungeonItemId
            race.generateWithRequired(zoneId)

            self.b_setGotoDungeon(self.air.district.doId, zoneId)

            return task.done

        task.delayTime = 1
        return task.again
