from .DistributedDungeonAI import DistributedDungeonAI
from direct.task.Task import Task

class DistributedRaceAI(DistributedDungeonAI):
    COUNTDOWN_TIME = 3

    def __init__(self, air):
        DistributedDungeonAI.__init__(self, air)

    def syncReady(self):
        avatarId = self.air.currentAvatarSender

        countDownTask = Task(self.__countDownTask)
        countDownTask.duration = self.COUNTDOWN_TIME

        taskMgr.add(countDownTask, self.uniqueName(avatarId), extraArgs = [avatarId], appendTask = True)

    def __countDownTask(self, avatarId: int, task: Task):
        if task.time >= task.duration:
            return Task.done
        else:
            self.sendUpdateToAvatarId(avatarId, 'setCountDown', [int(task.duration - task.time)])

            return Task.cont
