from game.cars.carplayer.InteractiveObjectAI import (
    CMD_TYPE_POSITIVE, COMMAND_OFFER_SPONSOR_BOOTH,
    COMMAND_OFFER_QUERY_INTERACTIONS, InteractiveObjectAI)

class SponsorBoothAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant SponsorBoothAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.assetId = 5007
        self.clientScript = "scripts/interactive/interact_switch.lua"

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_QUERY_INTERACTIONS:
            self.setState(70) # Interaction radius
            self.d_setInteractiveCommands(avatarId, eventId, [COMMAND_OFFER_SPONSOR_BOOTH, self.getCatalogId(), CMD_TYPE_POSITIVE])