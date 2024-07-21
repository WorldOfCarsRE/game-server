
from game.cars.dungeon.DistributedDungeonAI import DistributedDungeonAI
from .Track import Track
from direct.task.Task import Task

class DistributedRaceAI(DistributedDungeonAI):
    COUNTDOWN_TIME = 4

    def __init__(self, air, track):
        DistributedDungeonAI.__init__(self, air)
        self.track: Track = track
        self.countDown: int = self.COUNTDOWN_TIME

    def syncReady(self):
        # TODO: Verify that everybody's ready, (and gathered the NPC players in SPRaceAI)

        # 0 so the countdown can start next frame
        self.doMethodLater(0, self.__doCountDown, self.taskName("countDown"))

    def __doCountDown(self, task: Task):
        self.countDown -= 1
        self.sendUpdate('setCountDown', (self.countDown,))
        if self.countDown == 0:
            return task.done

        task.delayTime = 1
        return task.again
