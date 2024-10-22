from game.cars.carplayer.InteractiveObjectAI import (
    CMD_TYPE_POSITIVE, COMMAND_OFFER_GAME, COMMAND_OFFER_PLAYER_APPROACH,
    COMMAND_SET_MAP_EFFECT, InteractiveObjectAI)


class DocsClinicAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant DocsClinicAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.assetId = 5000
        self.catalogId = 103
        self.name = "landmark_docsclinic"
        self.minigameId = 106

        # NOTE: This does not work so we use the `default_npc` script.
        # self.clientScript = "scripts/interactive/minigame_entry.lua"

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_PLAYER_APPROACH:
            av = self.air.getDo(avatarId)
            av.d_showDialogs(self.minigameId, [str(self.catalogId)])
