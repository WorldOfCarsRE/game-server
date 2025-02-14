from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.DistributedObjectUD import DistributedObjectUD
from . import ShardGlobals
from typing import Dict

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

    def getPopulationLevel(self, shardPop) -> int:
        # TODO
        return ShardGlobals.POPULATION_LEVEL_NONE

    def getShardChannel(self, shardId) -> int:
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
