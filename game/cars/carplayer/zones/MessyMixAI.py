from game.cars.carplayer.InteractiveObjectAI import (
    COMMAND_OFFER_PLAYER_APPROACH,
    InteractiveObjectAI)

class MessyMixAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant MessyMixAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.assetId = 5005
        #self.clientScript = "scripts/interactive/water_tower.lua"

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_PLAYER_APPROACH:
            # TODO
            pass