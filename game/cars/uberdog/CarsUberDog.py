"""
The Cars Uber Distributed Object Globals server.
"""

from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.PyDatagram import PyDatagram

from game.cars.ai.CarsAIMsgTypes import *
from game.cars.distributed.CarsGlobals import *
from game.cars.lobby.DistributedTutorialLobbyUD import DistributedTutorialLobbyUD
from game.otp.ai.AIDistrict import AIDistrict
from game.otp.distributed.OtpDoGlobals import *
from game.otp.uberdog.UberDog import UberDog

from .ShardManagerUD import ShardManagerUD


class CarsUberDog(UberDog):
    notify = directNotify.newCategory("UberDog")

    def __init__(
            self, mdip, mdport, esip, esport, dcFilenames,
            serverId, minChannel, maxChannel):
        assert self.notify.debugStateCall(self)

        UberDog.__init__(
            self, mdip, mdport, esip, esport, dcFilenames,
            serverId, minChannel, maxChannel)

        self.generateDungeonMap: dict[int, function] = {}

    def getGameDoId(self):
        return OTP_DO_ID_CARS

    def createObjects(self):
        UberDog.createObjects(self)

        # Ask for the ObjectServer so we can check the dc hash value
        context = self.allocateContext()
        self.queryObjectAll(self.serverId, context)

        self.holidayManager = self.generateGlobalObject(OTP_DO_ID_CARS_HOLIDAY_MANAGER, "HolidayManager")

        # ShardManager has to be an object on the state server because the game
        # expects some things (like the tutorial and yards) to generate as this object's
        # parent.
        self.shardManager = ShardManagerUD(self)
        # HACK: parentId has to be set as at least something to prevent message truncation.
        self.shardManager.generateWithRequiredAndId(OTP_DO_ID_CARS_SHARD_MANAGER, 1, 0)
        self.setAIReceiver(OTP_DO_ID_CARS_SHARD_MANAGER)

        self.tutorialLobby = DistributedTutorialLobbyUD(self)
        self.tutorialLobby.generateOtpObject(OTP_DO_ID_CARS_SHARD_MANAGER, 100)

    def handlePlayGame(self, msgType, di):
        # Handle Cars specific message types before
        # calling the base class
        if msgType == CARS_GENERATE_DUNGEON_RESP:
            self.handleGenerateDungeonResp(di)
        else:
            AIDistrict.handlePlayGame(self, msgType, di)

    def remoteGenerateDungeon(self, aiChannel, dungeonType, lobbyDoId, contextDoId, playerIds, callback):
        context = self.allocateContext()
        self.generateDungeonMap[context] = callback
        dg = PyDatagram()
        dg.addServerHeader(aiChannel, self.ourChannel, CARS_GENERATE_DUNGEON)
        dg.addUint32(context)
        dg.addUint8(dungeonType)
        dg.addUint32(lobbyDoId)
        dg.addUint32(contextDoId)

        for playerId in playerIds:
            dg.addUint32(playerId)

        self.send(dg)

    def handleGenerateDungeonResp(self, di):
        context = di.getUint32()
        callback = self.generateDungeonMap.get(context)
        if callback:
            del self.generateDungeonMap[context]
            doId = di.getUint32()
            parentId = di.getUint32()
            zoneId = di.getUint32()
            callback(doId, parentId, zoneId)
        else:
            self.notify.warning("Ignoring unexpected context %d for CARS_GENERATE_DUNGEON" % context)


