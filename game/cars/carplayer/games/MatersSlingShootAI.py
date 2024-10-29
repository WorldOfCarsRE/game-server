from game.cars.carplayer.InteractiveObjectAI import (
    COMMAND_OFFER_PLAYER_APPROACH, InteractiveObjectAI)


class MatersSlingShootAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant MatersSlingShootAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.assetId = 5000
        self.catalogId = 61005

        # TODO: No landmark in XML for this minigame?
        self.name = ""

        self.minigameId = 108

        self.clientScript = "scripts/interactive/default_npc_no_physics.lua"

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_PLAYER_APPROACH:
            av = self.air.getDo(avatarId)
            av.d_showDialogs(self.minigameId, [str(self.catalogId)])
