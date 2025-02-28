from game.cars.carplayer.InteractiveObjectAI import (
    COMMAND_OFFER_PLAYER_APPROACH,
    InteractiveObjectAI)

class WaterTowerAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant WaterTowerAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.assetId = 5006
        self.clientScript = "scripts/interactive/water_tower.lua"

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_PLAYER_APPROACH:
            # TODO: Sync sound effects with animation loops
            self.d_broadcastChoreography([[2, 1], [4, 1], [6, 10], [8, 1]], [[54026, 1], [54027, 1]], [], [])