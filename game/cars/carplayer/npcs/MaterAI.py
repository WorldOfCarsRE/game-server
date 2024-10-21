from game.cars.carplayer.InteractiveObjectAI import InteractiveObjectAI
from game.cars.carplayer.InteractiveObjectAI import COMMAND_OFFER_QUERY_INTERACTIONS, COMMAND_SET_MAP_EFFECT, CMD_TYPE_POSITIVE
from game.cars.carplayer.InteractiveObjectAI import TYPE_NPC

class MaterAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant MaterAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.objType = TYPE_NPC
        self.assetId = 31009 # materCatalogItemId
        self.catalogId = 102

    def announceGenerate(self) -> None:
        InteractiveObjectAI.announceGenerate(self)

        # Experiments
        self.d_setTelemetry(3329, 1889, 0, 13073, 6027, 12847, -32722, 325026)

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_QUERY_INTERACTIONS:
            self.d_setInteractiveCommands(avatarId, eventId, [COMMAND_SET_MAP_EFFECT, self.getCatalogId(), CMD_TYPE_POSITIVE])
