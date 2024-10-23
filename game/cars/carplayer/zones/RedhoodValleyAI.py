from game.cars.carplayer.InteractiveObjectAI import (
    CMD_TYPE_POSITIVE, COMMAND_OFFER_QUERY_INTERACTIONS,
    COMMAND_SET_MAP_EFFECT, InteractiveObjectAI)


class RedhoodValleyAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant RedhoodValleyAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.assetId = 5000
        self.catalogId = 102
        self.name = 'zone_redhoodValley'

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_QUERY_INTERACTIONS:
            self.d_setInteractiveCommands(avatarId, eventId, [COMMAND_SET_MAP_EFFECT, self.getCatalogId(), CMD_TYPE_POSITIVE])
