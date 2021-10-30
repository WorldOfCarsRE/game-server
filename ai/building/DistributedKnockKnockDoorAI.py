from ai.building.DistributedAnimatedPropAI import DistributedAnimatedPropAI
from direct.task.Task import Task

class DistributedKnockKnockDoorAI(DistributedAnimatedPropAI):

    def __init__(self, air, propId):
        DistributedAnimatedPropAI.__init__(self, air, propId)

        self.fsm.setName('DistributedKnockKnockDoor')

        self.propId = propId
        self.doLaterTask = None

    def enterOff(self):
        DistributedAnimatedPropAI.enterOff(self)

    def exitOff(self):
        DistributedAnimatedPropAI.exitOff(self)

    def attractTask(self, task):
        self.fsm.request('attract')
        return Task.done

    def enterAttract(self):
        DistributedAnimatedPropAI.enterAttract(self)

    def exitAttract(self):
        DistributedAnimatedPropAI.exitAttract(self)

    def enterPlaying(self):
        DistributedAnimatedPropAI.enterPlaying(self)

        self.doLaterTask = taskMgr.doMethodLater(9, self.attractTask, self.uniqueName('knockKnock-timer'))

    def exitPlaying(self):
        DistributedAnimatedPropAI.exitPlaying(self)

        taskMgr.remove(self.doLaterTask)
        self.doLaterTask = None