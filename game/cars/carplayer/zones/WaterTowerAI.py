from direct.fsm.FSM import FSM

from game.cars.carplayer.InteractiveObjectAI import (
    COMMAND_OFFER_QUERY_INTERACTIONS,
    COMMAND_OFFER_PLAYER_APPROACH,
    InteractiveObjectAI)

# This matches the frames specified in API
FRAME_IDLE = 0
FRAME_END_IDLE = 1
FRAME_LEVER = 2
FRAME_END_LEVER = 3
FRAME_WATER_ON = 4
FRAME_END_WATER_ON = 5
FRAME_WATER_FLOW = 6
FRAME_END_WATER_FLOW = 7
FRAME_WATER_OFF = 8
FRAME_END_WATER_OFF = 9

LEVER_SOUND_ITEM = 54026
WATER_SOUND_ITEM = 54027

class WaterTowerAI(InteractiveObjectAI, FSM):
    notify = directNotify.newCategory('WaterTowerAI')

    def __init__(self, air) -> None:
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant WaterTowerAI dclass.
        self.__class__.__name__ = "InteractiveObjectAI"

        InteractiveObjectAI.__init__(self, air)
        FSM.__init__(self, hash(self))

        self.assetId = 5006
        self.clientScript = "scripts/interactive/water_tower.lua"

    def handleInteraction(self, avatarId: int, eventId: int, args: list) -> None:
        if eventId == COMMAND_OFFER_QUERY_INTERACTIONS:
            if self.getCurrentOrNextState() == "Off":
                self.d_broadcastChoreographyToPlayer(avatarId, [[FRAME_IDLE, 1]], [], [], [])
            elif self.getCurrentOrNextState() == "LeverOn":
                self.d_broadcastChoreographyToPlayer(avatarId, [[FRAME_END_LEVER, 1]], [], [], [])
            elif self.getCurrentOrNextState() == "WaterFlow":
                self.d_broadcastChoreographyToPlayer(avatarId, [[FRAME_WATER_FLOW, 15]], [], [], [])
            elif self.getCurrentOrNextState() == "WaterOff":
                self.d_broadcastChoreographyToPlayer(avatarId, [[FRAME_END_WATER_OFF, 1]], [], [], [])
        if eventId == COMMAND_OFFER_PLAYER_APPROACH:
            if self.getCurrentOrNextState() == "Off":
                self.request("LeverOn")

    def enterOff(self):
        self.d_broadcastChoreography([[FRAME_IDLE, 1]], [], [], [])

    def enterLeverOn(self):
        self.d_broadcastChoreography([[FRAME_LEVER, 1]], [[LEVER_SOUND_ITEM, 1]], [], [])
        taskMgr.doMethodLater(1, self.requestTask, self.taskName("WaterFlow"), extraArgs = ["WaterFlow"])

    def enterWaterFlow(self):
        self.d_broadcastChoreography([[FRAME_WATER_ON, 1], [FRAME_WATER_FLOW, 15]], [[WATER_SOUND_ITEM, 1]], [], [])
        taskMgr.doMethodLater(10, self.requestTask, self.taskName("WaterOff"), extraArgs = ["WaterOff"])

    def enterWaterOff(self):
        self.d_broadcastChoreography([[FRAME_WATER_OFF, 1]], [], [], [])
        taskMgr.doMethodLater(1, self.requestTask, self.taskName("Off"), extraArgs = ["Off"])

    def requestTask(self, name, *args):
        self.request(name, *args)

