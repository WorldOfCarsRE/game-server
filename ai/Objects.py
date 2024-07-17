from ai.DistributedObjectGlobalAI import DistributedObjectGlobalAI
from otp.constants import OTP_DO_ID_CARS_SHARD_MANAGER, OTP_DO_ID_CARS_HOLIDAY_MANAGER
from otp.constants import DUNGEON_INTEREST_HANDLE, DEFAULT_DUNGEON_ZONE
from .DistributedObjectAI import DistributedObjectAI
from direct.directnotify.DirectNotifyGlobal import directNotify
from typing import List
from ai.yard.DistributedYardAI import DistributedYardAI
from ai.dungeon.DistributedDungeonAI import DistributedDungeonAI

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
    # TODO FIXME: This should actually be a UberDOG.

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

    def getAllShardsRequest(self, context: int):
        avatarId = self.air.currentAvatarSender

        response = []
        response.append([self.air.district.doId, self.air.district.name, POPULATION_LEVEL_NONE, 0, self.air.district.getAvailable()])

        self.sendUpdateToAvatar(avatarId, 'getAllShardsResponse', [context, response])

    def getYardRequest(self, ownerDoId: int):
        yard = DistributedYardAI(self.air)
        yard.owner = ownerDoId
        yard.dungeonItemId = 10001
        self.air.generateWithRequired(yard, self.air.district.doId, ownerDoId)

        self.sendUpdateToAvatar(ownerDoId, 'getYardResponse', [self.air.district.doId, yard.doId])

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
        return self.catalogItemId

    def getInteractiveObjectCount(self):
        return len(self.interactiveObjects)

    def updateObjectCount(self):
        self.sendUpdate('setInteractiveObjectCount', [self.getInteractiveObjectCount()])

    def getPlayerCount(self):
        return len(self.playersInZone)

    def getMute(self):
        return self.mute

class DistributedTutorialLobbyContextAI(DistributedLobbyContextAI):
    def __init__(self, air):
        DistributedLobbyContextAI.__init__(self, air)

class DistributedLobbyAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.dungeonItemId: int = 1000

    def getDungeonItemId(self):
        return self.dungeonItemId

    def getHotSpotName(self):
        return ''

    def join(self):
        avatarId = self.air.currentAvatarSender

        zoneId = self.air.allocateZone()

        lobbyContext = DistributedTutorialLobbyContextAI(self.air)
        lobbyContext.owningAv = avatarId
        lobbyContext.playersInContext.append(avatarId)
        self.air.generateWithRequired(lobbyContext, DUNGEON_INTEREST_HANDLE, zoneId)

        dungeon = DistributedDungeonAI(self.air)
        dungeon.playerIds.append(avatarId)
        dungeon.lobbyDoId = self.doId
        dungeon.contextDoId = lobbyContext.doId
        self.air.generateWithRequired(dungeon, self.doId, zoneId)

        self.sendUpdateToAvatar(avatarId, 'gotoLobbyContext', [zoneId])

        lobbyContext.b_setGotoDungeon(self.air.district.doId, dungeon.zoneId)

class DistributedTutorialLobbyAI(DistributedLobbyAI):
    def __init__(self, air):
        DistributedLobbyAI.__init__(self, air)
