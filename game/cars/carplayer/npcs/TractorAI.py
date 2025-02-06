from direct.task.Task import Task

from game.cars.carplayer.InteractiveObjectAI import (
    COMMAND_OFFER_PLAYER_HONK,
    TYPE_NPC, InteractiveObjectAI)

STATE_NORMAL = 1
STATE_TIPPED = 2

class TractorAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant TractorAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.objType = TYPE_NPC
        self.assetId = 31015 # tractorCatalogItemId

    def announceGenerate(self) -> None:
        InteractiveObjectAI.announceGenerate(self)

        # Experiments
        self.d_setTelemetry(2574, 2404, 0, -1354, 511, -12706, -16656, 77309)

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_PLAYER_HONK:
            if self.getState() != STATE_TIPPED:
                self.setState(STATE_TIPPED)
                self.d_broadcastChoreography([[33269, 1], [33271, 5], [33272, 1]], [[54010, 1], [54011, 1]], [[32010, 1]], [[0, 0]])

                taskMgr.doMethodLater(12, self._returnToNormalState, self.taskName(f"returnToNormalState-{self.getName()}"))

    def _returnToNormalState(self, task: Task):
        self.setState(STATE_NORMAL)

        return task.done