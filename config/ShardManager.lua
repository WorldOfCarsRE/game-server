OTP_DO_ID_CARS_SHARD_MANAGER = 4757
STATESERVER_OBJECT_UPDATE_FIELD = 2004

POPULATION_LEVEL_NONE = 0
POPULATION_LEVEL_VERY_LIGHT = 1
POPULATION_LEVEL_LIGHT = 2
POPULATION_LEVEL_MEDIUM = 3
POPULATION_LEVEL_FULL = 4
POPULATION_LEVEL_VERY_FULL = 5

Shards = {}

-- Internal messages (used by the AI)
SHARDMANAGER_REGISTER_SHARD = 20000
SHARDMANAGER_UPDATE_SHARD = 20001
SHARDMANAGER_DELETE_SHARD = 20002

-- Load the configuration varables (see config.example.lua)
dofile("config.lua")

local inspect = require('inspect')

function init(participant)
    participant:subscribeChannel(OTP_DO_ID_CARS_SHARD_MANAGER)
end

function handleDatagram(participant, msgType, dgi)
    if msgType == STATESERVER_OBJECT_UPDATE_FIELD then
        if dgi:readUint32() == OTP_DO_ID_CARS_SHARD_MANAGER then
            participant:handleUpdateField(dgi, "ShardManager")
        end
    elseif msgType == SHARDMANAGER_REGISTER_SHARD then
        handleRegister(participant, dgi)
    elseif msgType == SHARDMANAGER_UPDATE_SHARD then
        handleUpdate(participant, dgi)
    elseif msgType == SHARDMANAGER_DELETE_SHARD then
        handleDelete(participant)
    else
        participant:warn(string.format("Got unknown message: %d", msgType))
    end
end

-- Messages sent internally (AI)
function handleRegister(participant, dgi)
    local sender = participant:getSender():tonumber()
    local shardId = dgi:readUint32()
    local shardName = dgi:readString()

    participant:debug(string.format("handleRegister(%d, %d, %s)", sender, shardId, shardName))
    Shards[sender] = {shardId, shardName, 0, 0}
end

function handleUpdate(participant, dgi)
    local sender = participant:getSender():tonumber()
    local avatarCount = dgi:readUint16()
    local active = dgi:readUint8()

    participant:debug(string.format("handleUpdate(%d, %d, %d)", sender, avatarCount, active))

    if Shards[sender] == nil then
        participant:warn(string.format("Got update for non-existant shard from sender %d", sender))
        return
    end

    Shards[sender][3] = avatarCount
    Shards[sender][4] = active
end

function handleDelete(participant)
    local sender = participant:getSender():tonumber()

    participant:debug(string.format("handleDelete(%d)", sender))

    if Shards[sender] == nil then
        participant:warn(string.format("Got delete for non-existant shard from sender %d", sender))
        return
    end
    Shards[sender] = nil
end

function getPopulationLevel(shardPop)
    local popLevel = POPULATION_LEVEL_NONE
    if shardPop >= POPULATION_LEVELS[POPULATION_LEVEL_VERY_FULL + 1] then
        popLevel = POPULATION_LEVEL_VERY_FULL
    elseif shardPop >= POPULATION_LEVELS[POPULATION_LEVEL_FULL + 1] and shardPop <= POPULATION_LEVELS[POPULATION_LEVEL_VERY_FULL + 1] then
        popLevel = POPULATION_LEVEL_FULL
    elseif shardPop >= POPULATION_LEVELS[POPULATION_LEVEL_MEDIUM + 1] and shardPop <= POPULATION_LEVELS[POPULATION_LEVEL_FULL + 1] then
        popLevel = POPULATION_LEVEL_MEDIUM
    elseif shardPop >= POPULATION_LEVELS[POPULATION_LEVEL_LIGHT + 1] and shardPop <= POPULATION_LEVELS[POPULATION_LEVEL_MEDIUM + 1] then
        popLevel = POPULATION_LEVEL_LIGHT
    elseif shardPop >= POPULATION_LEVELS[POPULATION_LEVEL_VERY_LIGHT + 1] and shardPop <= POPULATION_LEVELS[POPULATION_LEVEL_LIGHT + 1] then
        popLevel = POPULATION_LEVEL_VERY_LIGHT
    end
    return popLevel
end

-- Field updates sent by the client:
function handleShardManager_getAllShardsRequest(participant, fieldId, data)
    local avatarId = participant:getAvatarIdFromSender()
    local context = data[1]
    participant:debug(string.format("getAllShardsRequest(%d, %d)", context, avatarId))

    local shards = {}
    for _, shard in pairs(Shards) do
        table.insert(shards, {shard[1], shard[2], getPopulationLevel(shard[3]), shard[3], shard[4]})
    end

    participant:sendUpdateToAvatarId(avatarId, OTP_DO_ID_CARS_SHARD_MANAGER,
                "ShardManager", "getAllShardsResponse", {context, shards})

end

function handleShardManager_getShardRequest(participant, fieldId, data)
    local avatarId = participant:getAvatarIdFromSender()

    local context = data[1]
    local shardId = data[2]
    participant:debug(string.format("getShardRequest(%d, %d, %d)", context, shardId, avatarId))

    for _, shard in pairs(Shards) do
        if shard[1] == shardId then
            participant:sendUpdateToAvatarId(avatarId, OTP_DO_ID_CARS_SHARD_MANAGER, "ShardManager", "getShardResponse", {context, {shard[1], shard[2], getPopulationLevel(shard[3]), shard[3], shard[4]}})
            return
        end
    end

    participant:warn(string.format("Got shard request for non-existant shard from avatar %d", avatarId))
end
