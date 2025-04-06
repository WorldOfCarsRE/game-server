from game.cars.carplayer.InteractiveObjectAI import (
    COMMAND_OFFER_PLAYER_APPROACH,
    TYPE_SPAWNED_SPRITE, InteractiveObjectAI)

HAZARD_STATE_LIVE = 1
HAZARD_STATE_DEAD = 2

class HazardAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant HazardAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.objType = TYPE_SPAWNED_SPRITE
        self.assetId = 5001
        self.name = "hazard"
        self.clientScript = "scripts/interactive/racing_hazard_oilSlick.lua"

    def announceGenerate(self) -> None:
        InteractiveObjectAI.announceGenerate(self)

        self.setState(HAZARD_STATE_LIVE)

        # Experiments
        self.d_setTelemetry(self.x, self.y, 0, 0, 0, 0, 0, 0)

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_PLAYER_APPROACH:
            if self.getState() != HAZARD_STATE_DEAD:
                self.setState(HAZARD_STATE_DEAD)
                self.d_broadcastChoreography([[4, 1]], [], [], [])