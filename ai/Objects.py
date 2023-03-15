from ai.DistributedObjectGlobalAI import DistributedObjectGlobalAI
from otp.constants import OTP_DO_ID_CARS_SHARD_MANAGER, OTP_DO_ID_CARS_HOLIDAY_MANAGER
from otp.constants import OTP_ZONE_ID_ELEMENTS, DEFAULT_DUNGEON_ZONE
from .DistributedObjectAI import DistributedObjectAI
from direct.directnotify.DirectNotifyGlobal import directNotify
from typing import List

class DistributedDistrictAI(DistributedObjectAI):

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.name = ''
        self.available = False

    def d_setName(self, name):
        self.sendUpdate('setName', [name])

    def b_setName(self, name):
        self.name = name
        self.d_setName(name)

    def getName(self):
        return self.name

    def d_setAvailable(self, available):
        self.sendUpdate('setAvailable', [available])

    def b_setAvailable(self, available):
        self.available = available
        self.d_setAvailable(available)

    def getAvailable(self):
        return self.available

    def getEnabled(self):
        return self.available

class CarsDistrictAI(DistributedDistrictAI):
    notify = directNotify.newCategory('CarsDistrictAI')

    def __init__(self, air):
        DistributedDistrictAI.__init__(self, air)

    def handleChildArrive(self, obj, zoneId):
        pass
        # if isinstance(obj, DistributedCarPlayer):
            # obj.sendUpdate('arrivedOnDistrict', [self.doId])
            # self.air.incrementPopulation()

POPULATION_LEVEL_NONE = 0
POPULATION_LEVEL_VERY_LIGHT = 1
POPULATION_LEVEL_LIGHT = 2
POPULATION_LEVEL_MEDIUM = 3
POPULATION_LEVEL_FULL = 4
POPULATION_LEVEL_VERY_FULL = 5

class ShardManagerUD(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

    def getAllShardsRequest(self, context):
        avatarId = self.air.currentAvatarSender
        print(f'getAllShardsRequest - {context}')

        response = []
        response.append([self.air.district.doId, self.air.district.name, POPULATION_LEVEL_NONE, 0, 1])

        self.sendUpdateToAvatar(avatarId, 'getAllShardsResponse', [context, response])

class HolidayManagerUD(DistributedObjectGlobalAI):
    doId = OTP_DO_ID_CARS_HOLIDAY_MANAGER

class CarPlayerStatusAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

    def getPrivacySettings(self):
        return 0

    def getLocationType(self):
        return 0

class DistributedZoneAI(DistributedObjectAI):
    def __init__(self, air, name, mapId):
        DistributedObjectAI.__init__(self, air)
        self.name = name
        self.mapId = mapId
        self.catalogItemId = mapId
        self.interactiveObjects = []
        self.playersInZone = []
        self.mute = 0

    def getName(self):
        return self.name

    def getMapId(self):
        return self.mapId

    def getCatalogItemId(self):
        return self.catalogItemId # 15001

    def getInteractiveObjectCount(self):
        return len(self.interactiveObjects)

    def getPlayerCount(self):
        return len(self.playersInZone)

    def getMute(self):
        return self.mute

class DistributedLobbyContextAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.playersInDungeon: List[int] = []
        self.playersInContext: List[int] = []
        self.owningAv: int = 0

        self.destinationShard: int = 0
        self.destinationZone: int = 0

    def getPlayersInDungeon(self):
        return self.playersInDungeon

    def getPlayersInContext(self):
        return self.playersInContext

    def getOwner(self):
        return self.owningAv

    def b_setGotoDungeon(self, destinationShard: int, destinationZone: int):
        self.destinationShard = destinationShard
        self.destinationZone = destinationZone

        self.sendUpdate('gotoDungeon', [destinationShard, destinationZone])

    def getGotoDungeon(self):
        return self.destinationShard, self.destinationZone

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

    def getWaitForObjects(self):
        return [] # self.playerIds

    def getDungeonItemId(self):
        return 1000

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


class DistributedTutorialLobbyContextAI(DistributedLobbyContextAI):
    def __init__(self, air):
        DistributedLobbyContextAI.__init__(self, air)

class DistributedLobbyAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

    def getDungeonItemId(self):
        return 1000

    def getHotSpotName(self):
        return ''

    def join(self):
        avatarId = self.air.currentAvatarSender

        zoneId = self.air.allocateZone()

        lobbyContext = DistributedTutorialLobbyContextAI(self.air)
        lobbyContext.owningAv = avatarId
        lobbyContext.playersInContext.append(avatarId)
        self.air.generateWithRequired(lobbyContext, OTP_ZONE_ID_ELEMENTS, zoneId)

        dungeon = DistributedDungeonAI(self.air)
        dungeon.playerIds.append(avatarId)
        dungeon.lobbyDoId = self.doId
        dungeon.contextDoId = lobbyContext.doId
        self.air.generateWithRequired(dungeon, self.doId, zoneId)

        # zone = DistributedZoneAI(self.air)
        # self.air.generateWithRequired(zone, dungeon.doId, DEFAULT_DUNGEON_ZONE)

        self.sendUpdateToAvatar(avatarId, 'gotoLobbyContext', [zoneId])

        lobbyContext.b_setGotoDungeon(self.air.district.doId, dungeon.zoneId)

class DistributedTutorialLobbyAI(DistributedLobbyAI):
    def __init__(self, air):
        DistributedLobbyAI.__init__(self, air)
