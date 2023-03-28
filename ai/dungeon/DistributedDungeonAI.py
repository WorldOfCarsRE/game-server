from ai.DistributedObjectAI import DistributedObjectAI
from typing import List

VIDEO_DONE_COMMAND = 1
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

    def getWaitForObjects(self):
        return [] # self.playerIds

    def getDungeonItemId(self):
        return self.dungeonItemId

    def getLobbyDoid(self):
        return self.lobbyDoId

    def getContextDoid(self):
        return self.contextDoId

    def setAiCommand(self, command, args):
        avatarId = self.air.currentAvatarSender
        print('setAICommand', command)
        # BUG: Supposidly VIDEO_DONE_COMMAND gets sent after video is finished, but
        # all command sent are 1003?  OTP Bug?
        if command == 1003:
            # self.sendUpdateToAvatar(avatarId, 'setClientCommand', [SHOW_DRIVING_CONTROLS, []])
            self.sendUpdateToAvatar(avatarId, 'setClientCommand', [GIVE_PLAYER_CAR_CONTROL, []])
