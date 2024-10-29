from game.cars.carplayer.InteractiveObjectAI import (
    CMD_TYPE_POSITIVE, COMMAND_OFFER_QUERY_INTERACTIONS,
    COMMAND_OFFER_SHOP, InteractiveObjectAI)


class FillmoreFizzyFuelHutAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant FillmoreFizzyFuelHutAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.assetId = 5000
        self.catalogId = 22011
        self.name = "isostore_FillmoreFizzyHutRV"

        self.clientScript = "scripts/interactive/fillmore_fizzy_shopaholic.lua"

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_QUERY_INTERACTIONS:
            self.d_setInteractiveCommands(avatarId, eventId, [COMMAND_OFFER_SHOP, self.getCatalogId(), CMD_TYPE_POSITIVE])
