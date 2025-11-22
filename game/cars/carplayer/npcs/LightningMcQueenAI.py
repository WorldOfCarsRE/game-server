from game.cars.carplayer.InteractiveObjectAI import (
    COMMAND_OFFER_QUERY_INTERACTIONS,
    TYPE_NPC, InteractiveObjectAI)


class LightningMcQueenAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant LightningMcQueenAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.objType = TYPE_NPC
        self.assetId = 31010

    def announceGenerate(self) -> None:
        InteractiveObjectAI.announceGenerate(self)

        # Experiments
        # TODO: More accurate placement?
        self.d_setTelemetry(3548, 1812, 0, 551, 854, 16213, 16156, 259154)

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_QUERY_INTERACTIONS:
            # Indicators: First visit (32024), Available quest (32025), Incomplete quest (32026), Complete quest (32027)
            self.d_broadcastChoreographyToPlayer(avatarId, [], [], [[32024, 0]], []) # Indicator
