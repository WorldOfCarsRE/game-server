from direct.distributed.DistributedObjectAI import DistributedObjectAI
from typing import List

VIDEO_DONE_COMMAND = 1
START_FRAME_MATER_BACKWARDS_DRIVING = 2
DRIVING_CONTROLS_SHOWN = 3
SHOW_DRIVING_CONTROLS = 1003
GIVE_PLAYER_CAR_CONTROL = 1007

class DistributedDungeonAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.playerIds: List[int] = []
        self.lobbyDoId: int = 0
        self.contextDoId: int = 0
        self.dungeonItemId: int = 1000
        self.interactiveObjects: list = []

    def getWaitForObjects(self):
        return [] # self.playerIds

    def getDungeonItemId(self):
        return self.dungeonItemId

    def getLobbyDoid(self):
        return self.lobbyDoId

    def getContextDoid(self):
        return self.contextDoId

    def setAiCommand(self, command, args):
        avatarId = self.air.getAvatarIdFromSender()
        print('setAICommand', command, args)

        if args[0] == VIDEO_DONE_COMMAND:
            # self.sendUpdateToAvatarId(avatarId, 'setClientCommand', [SHOW_DRIVING_CONTROLS, []])
            self.sendUpdateToAvatarId(avatarId, 'setClientCommand', [GIVE_PLAYER_CAR_CONTROL, []])

        elif args[0] == START_FRAME_MATER_BACKWARDS_DRIVING:
            for obj in self.interactiveObjects:
                if obj.name == "Mater":
                    obj.d_broadcastChoreography([[112, 1], [113, 5], [114, 1]], [[54022, 1], [54023, 0]], [[0, 0]], [[0, 0]])
