from game.cars.carplayer.InteractiveObjectAI import (
    COMMAND_OFFER_PLAYER_APPROACH,
    InteractiveObjectAI)

STATE_VISIBLE = 1
STATE_EXPLODE = 2

class HayBaleBombAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant HayBaleBombAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.assetId = 5004
        self.clientScript = "scripts/interactive/hay_bale_bomb.lua"

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_PLAYER_APPROACH:
            if self.getState() != STATE_EXPLODE:
                self.setState(STATE_EXPLODE)
                self.d_broadcastChoreography([[3, 1]], [[54024, 1]], [], [])
                
                taskMgr.doMethodLater(5, self._restoreHayBaleState, self.taskName(f"restoreNormalState-{self.getName()}"))

    def _restoreHayBaleState(self, task):
        self.setState(STATE_VISIBLE)
        self.d_broadcastChoreography([[1, 1]], [], [], [])

        return task.done