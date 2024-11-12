from direct.distributed.DistributedObjectGlobalUD import DistributedObjectGlobalUD
from . import ShardGlobals
from typing import Dict

class Shard:
    shardId: int
    shardName: str
    populationLevel: int
    avatarCount: int
    active: int

class ShardManagerUD(DistributedObjectGlobalUD):
    notify = directNotify.newCategory('ShardManagerUD')
    notify.setDebug(True)

    def __init__(self, air):
        DistributedObjectGlobalUD.__init__(self, air)

        self.shardInfo: Dict[int, Shard] = {}

    def getPopulationLevel(self, shardPop) -> int:
        # TODO
        return ShardGlobals.POPULATION_LEVEL_NONE

    def handleRegister(self, di):
        sender = self.air.getMsgSender()

        shardId = di.getUint32()
        shardName = di.getString()

        shard = Shard()
        shard.shardId = shardId
        shard.shardName = shardName
        shard.populationLevel = ShardGlobals.POPULATION_LEVEL_NONE
        shard.avatarCount = 0
        shard.active = 0

        self.shardInfo[sender] = shard

        self.notify.debug(f'Registered shard: {shardName}!')

    def handleUpdate(self, di):
        sender = self.air.getMsgSender()

        avatarCount = di.getUint16()
        active = di.getUint8()

        if sender in self.shardInfo:
            shard = self.shardInfo[sender]

            shard.avatarCount = avatarCount
            shard.active = active

    def getAllShardsRequest(self, context):
        self.notify.debug(f'getAllShardsRequest: {context}')

        avatarId = self.air.getAvatarIdFromSender()
        response = []

        for shard in self.shardInfo.values():
            response.append([shard.shardId, shard.shardName, self.getPopulationLevel(shard.avatarCount), shard.avatarCount, shard.active])

        self.sendUpdateToAvatarId(avatarId, 'getAllShardsResponse', [context, response])
