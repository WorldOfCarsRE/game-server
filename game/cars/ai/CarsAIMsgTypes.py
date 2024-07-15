from game.otp.ai.AIMsgTypes import *
CarsAIMsgName2Id = {
# ShardManager messages:
 'SHARDMANAGER_REGISTER_SHARD': 20000,
 'SHARDMANAGER_UPDATE_SHARD': 20001,
 'SHARDMANAGER_DELETE_SHARD': 20002}
CarsAIMsgId2Names = invertDictLossless(CarsAIMsgName2Id)
for name, value in list(CarsAIMsgName2Id.items()):
    exec('%s = %s' % (name, value))

del name
del value
