from game.otp.ai.AIMsgTypes import *
CarsAIMsgName2Id = {
    # PlayerFriendsManager messages:
    'FRIENDMANAGER_ACCOUNT_ONLINE': 10000,
    'FRIENDMANAGER_ACCOUNT_OFFLINE': 10001,
    'FRIENDMANAGER_INVITE_RACE': 10002,
    'FRIENDMANAGER_INVITE_RESP': 10003,
    # ShardManager messages:
    'SHARDMANAGER_ONLINE': 20000,
    # Lobby/Dungeon messages (For Cars AI and UD):
    'CARS_GENERATE_DUNGEON': 30000,
    'CARS_GENERATE_DUNGEON_RESP': 30001}
CarsAIMsgId2Names = invertDictLossless(CarsAIMsgName2Id)
for name, value in list(CarsAIMsgName2Id.items()):
    exec('%s = %s' % (name, value))

del name
del value
