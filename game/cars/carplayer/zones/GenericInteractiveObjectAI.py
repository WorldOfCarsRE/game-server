from game.cars.carplayer.InteractiveObjectAI import InteractiveObjectAI


class GenericInteractiveObjectAI(InteractiveObjectAI):
    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant GenericInteractiveObjectAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)

        self.assetId = 5000
        self.clientScript = "scripts/interactive/generic_interactive_object.lua"
