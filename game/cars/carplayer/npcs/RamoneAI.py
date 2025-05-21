from game.cars.carplayer.InteractiveObjectAI import (
    CMD_TYPE_POSITIVE, COMMAND_OFFER_QUERY_INTERACTIONS,
    COMMAND_OFFER_QUEST_ACCEPT, TYPE_NPC, InteractiveObjectAI)


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

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_QUERY_INTERACTIONS:
            # Indicators: First visit (32024), Available quest (32025), Incomplete quest (32026), Complete quest (32027)
            self.d_broadcastChoreographyToPlayer(avatarId, [], [], [[32024, 0]], [])
            
            self.d_setInteractiveCommands(avatarId, eventId, [COMMAND_OFFER_QUEST_ACCEPT, self.getCatalogId(), CMD_TYPE_POSITIVE])
