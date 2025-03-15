import json

from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.DistributedObjectUD import DistributedObjectUD
from . import ShardGlobals
from typing import Dict
from game.cars.distributed.CarsGlobals import DUNGEON_TYPE_YARD

class Shard:
    shardId: int
    shardName: str
    populationLevel: int
    avatarCount: int
    active: int

class ShardManagerUD(DistributedObjectUD):
    notify = directNotify.newCategory('ShardManagerUD')

    def __init__(self, air):
        DistributedObjectUD.__init__(self, air)

        self.shardInfo: Dict[int, Shard] = {}

    def getPopulationLevel(self, shardPop: int) -> int:
        levels: list[int] = json.loads(config.GetString('shard-population-levels'))

        popLevel = ShardGlobals.POPULATION_LEVEL_NONE
        if shardPop >= levels[ShardGlobals.POPULATION_LEVEL_VERY_FULL]:
            popLevel = ShardGlobals.POPULATION_LEVEL_VERY_FULL
        elif shardPop >= levels[ShardGlobals.POPULATION_LEVEL_FULL] and shardPop <= levels[ShardGlobals.POPULATION_LEVEL_VERY_FULL]:
            popLevel = ShardGlobals.POPULATION_LEVEL_FULL
        elif shardPop >= levels[ShardGlobals.POPULATION_LEVEL_MEDIUM] and shardPop <= levels[ShardGlobals.POPULATION_LEVEL_FULL]:
            popLevel = ShardGlobals.POPULATION_LEVEL_MEDIUM
        elif shardPop >= levels[ShardGlobals.POPULATION_LEVEL_LIGHT] and shardPop <= levels[ShardGlobals.POPULATION_LEVEL_MEDIUM]:
            popLevel = ShardGlobals.POPULATION_LEVEL_LIGHT
        elif shardPop >= levels[ShardGlobals.POPULATION_LEVEL_VERY_LIGHT] and shardPop <= levels[ShardGlobals.POPULATION_LEVEL_LIGHT]:
            popLevel = ShardGlobals.POPULATION_LEVEL_VERY_LIGHT
        return popLevel

    def getShardChannel(self, shardId: int) -> int:
        for sender, shard in self.shardInfo.items():
            if shard.shardId == shardId:
                return sender

        self.notify.warning(f"Couldn't find AI Channel for shard: {shardId}")
        return 0

    def announceGenerate(self):
        DistributedObjectUD.announceGenerate(self)
        self.air.sendOnline()

    # AI -> UD
    def registerShard(self, shardId, shardName):
        sender = self.air.getMsgSender()

        shard = Shard()
        shard.shardId = shardId
        shard.shardName = shardName
        shard.populationLevel = ShardGlobals.POPULATION_LEVEL_NONE
        shard.avatarCount = 0
        shard.active = 0

        self.shardInfo[sender] = shard

        self.notify.debug(f'Registered shard: {shardName}!  Sender: {sender}')

    def updateShard(self, avatarCount, active):
        sender = self.air.getMsgSender()

        if sender in self.shardInfo:
            shard = self.shardInfo[sender]

            shard.avatarCount = avatarCount
            shard.active = active
            self.notify.debug(f"Shard {shard.shardName} has been updated.  avatarCount: {avatarCount}, active: {active}")
        else:
            self.notify.warning(f"No shard under sender: {sender}")

    def deleteShard(self):
        sender = self.air.getMsgSender()

        if sender in self.shardInfo:
            self.notify.debug(f"Deleting shard {self.shardInfo[sender].shardName}.")
            del self.shardInfo[sender]
        else:
            self.notify.warning(f"Got \"deleteShard\" from unknown sender: {sender}")

    # CLIENT -> UD
    def getAllShardsRequest(self, context):
        self.notify.debug(f'getAllShardsRequest: {context}')

        sender = self.air.getMsgSender()
        response = []

        for shard in self.shardInfo.values():
            response.append([shard.shardId, shard.shardName, self.getPopulationLevel(shard.avatarCount), shard.avatarCount, shard.active])

        self.sendUpdateToChannel(sender, 'getAllShardsResponse', [context, response])

    def getYardRequest(self, ownerDoId: int) -> None:
        def gotAvatarLocation(doId: int, parentId: int, zoneId: int) -> None:
            if ownerDoId != doId:
                self.notify.warning(f"Got unexpected location for doId {doId}, was expecting {ownerDoId}!")
                return

            # Get the AI channel of the avatar's shard:
            shardChannel = self.getShardChannel(parentId)
            if not shardChannel:
                self.notify.warning(f"No shardChannel")
                return

            def gotYard(doId: int, parentId: int, zoneId: int) -> None:
                self.sendUpdateToAvatarId(ownerDoId, "getYardResponse", [parentId, doId])

            self.air.remoteGenerateDungeon(shardChannel, DUNGEON_TYPE_YARD, self.doId, 0, [ownerDoId], gotYard)

        self.air.getObjectLocation(ownerDoId, gotAvatarLocation)
