from game.cars.carplayer.InteractiveObjectAI import InteractiveObjectAI
from game.cars.carplayer.InteractiveObjectAI import COMMAND_OFFER_QUERY_INTERACTIONS, COMMAND_OFFER_QUEST_ACCEPT, CMD_TYPE_POSITIVE
from game.cars.carplayer.InteractiveObjectAI import TYPE_NPC

class RamoneAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant RamoneAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.objType = TYPE_NPC
        self.assetId = 31008 # ramoneCatalogItemId
        self.catalogId = 25010

    def announceGenerate(self) -> None:
        InteractiveObjectAI.announceGenerate(self)

        # Experiments
        self.d_setTelemetry(1806, 860, 0, 1522, 1329, 15022, -3515, 136708)

    # def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        # if eventId == COMMAND_OFFER_QUERY_INTERACTIONS:
            # self.d_setInteractiveCommands(avatarId, eventId, [COMMAND_OFFER_QUEST_ACCEPT, self.getCatalogId(), CMD_TYPE_POSITIVE])
