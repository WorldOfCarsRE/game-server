from .DistributedDungeonAI import DistributedDungeonAI
from game.cars.carplayer.npcs.TutorialTruckAI import TutorialTruckAI
from game.cars.carplayer.npcs.TutorialMaterAI import TutorialMaterAI
from game.cars.distributed.CarsGlobals import *

VIDEO_DONE_COMMAND = 1
START_FRAME_MATER_BACKWARDS_DRIVING = 2
DRIVING_CONTROLS_SHOWN = 3
SHOW_DRIVING_CONTROLS = 1003
GIVE_PLAYER_CAR_CONTROL = 1007

class DistributedTutorialDungeonAI(DistributedDungeonAI):
    def __init__(self, air):
        # HACK: Renaming our class name here because
        # DistributedObjectAI will search dclassesByName
        # for the non-existant TutorialMaterAI dclass.
        self.__class__.__name__ = "DistributedDungeonAI"
        DistributedDungeonAI.__init__(self, air)

        self.dungeonItemId = 1000

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

    def createObjects(self):
        truck = TutorialTruckAI(self.air)
        truck.generateOtpObject(self.doId, DEFAULT_DUNGEON_ZONE)
        self.interactiveObjects.append(truck)

        mater = TutorialMaterAI(self.air)
        mater.generateOtpObject(self.doId, DEFAULT_DUNGEON_ZONE)
        self.interactiveObjects.append(mater)


