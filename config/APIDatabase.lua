DBSERVER_CREATE_STORED_OBJECT      = 1003
DBSERVER_CREATE_STORED_OBJECT_RESP = 1004

DBSERVER_GET_STORED_VALUES         = 1012
DBSERVER_GET_STORED_VALUES_RESP    = 1013

DBSERVER_SET_STORED_VALUES         = 1014

DATABASE_ID = 4003

-- This is act as a database server to bridge with the
-- API server, which hosts its own database.

-- Load the configuration varables (see config.example.lua)
dofile("config.lua")

local API_BASE

local http = require("http")
local json = require("json")
local inspect = require("inspect")

if PRODUCTION_ENABLED then
    API_BASE = "https://dxd.sunrise.games/carsds/api/internal/"
else
    API_BASE = "http://localhost/carsds/api/internal/"
end

function retrieveObject(participant, doId)
    local connAttempts = 0

    while (connAttempts < 3) do
        local response, error_message = http.get(API_BASE .. string.format("retrieveObject/%d", doId), {
            headers={
                ["User-Agent"]=USER_AGENT,
                ["Authorization"]=API_TOKEN
            }
        })

        if error_message then
            participant:error(string.format("retrieveObject returned an error! \"%s\"", error_message))
            connAttempts = connAttempts + 1
            goto retry
        end

        if response.status_code ~= 200 then
            participant:error(string.format("retrieveObject returned %d!, \"%s\"", response.status_code, response.body))
            connAttempts = connAttempts + 1
            goto retry
        end

        do
            -- If we're here, then we can return the response body.
            return true, response.body
        end

        -- retry goto to iterate again if we failed to retrieve our car data.
        ::retry::
    end

    -- If we're here, then we failed to get valid car data. Send an error response
    return false, ""
end

function updateObject(participant, doId, data)
    local connAttempts = 0

    while (connAttempts < 3) do
        local response, error_message = http.post(API_BASE .. string.format("updateObject/%d", doId), {
            body=json.encode(data),
            headers={
                ["User-Agent"]=USER_AGENT,
                ["Authorization"]=API_TOKEN,
                ["Content-Type"]="application/json"
            }
        })

        if error_message then
            participant:error(string.format("updateObject returned an error! \"%s\"", error_message))
            connAttempts = connAttempts + 1
            goto retry
        end

        if response.status_code ~= 200 then
            participant:error(string.format("updateObject returned %d!, \"%s\"", response.status_code, response.body))
            connAttempts = connAttempts + 1
            goto retry
        end

        do
            -- If we're here, then we can return the response body.
            return true, response.body
        end

        -- retry goto to iterate again if we failed to retrieve our car data.
        ::retry::
    end

    -- If we're here, then we failed to get valid car data. Send an error response
    return false, ""
end

-- NOTE: setDNA is handled on its own
Api2Field = {
    -- TODO: Figure out the rest
    -- Account
    lastLogin = "LAST_LOGIN",
    -- DistributedRaceCar
    totalMiles = "setMiles",
    racingPoints = "setRacingPoints",
    consumableSlot = "setConsumableSlot",
    consumableStack = "setConsumableStack",
    dashboardTextureId = "setDashboardTexture",
    raceSeries = "setRaceSeries",
    activeSponsorId = "setActiveSponsor",
    activeGearId = "setActiveGear",
    consumableItemList = "setConsumables",
    gears = "setGears",

    -- DistributedCarPlayer
    carCoins = "setCarCoins",
    userId = "setDISLid",
    animationList = "setAnimations",

    -- CarPlayerStatus
    setLocationType = "setLocationType",
    setPrivacySettings = "setPrivacySettings"
}

Field2Api = {}
for key, value in pairs(Api2Field) do
    Field2Api[value] = key
end

function init(participant)
    participant:subscribeChannel(DATABASE_ID)
end

function handleDatagram(participant, msgType, dgi)
    if msgType == DBSERVER_CREATE_STORED_OBJECT then
        participant:warn("CreateStoredObject not supported.")
    elseif msgType == DBSERVER_GET_STORED_VALUES then
        handleGetStoredValues(participant, dgi)
    elseif msgType == DBSERVER_SET_STORED_VALUES then
        handleSetStoredValues(participant, dgi)
    end
end

function handleGetStoredValues(participant, dgi)
    local sender = participant:getSender()
    local context = dgi:readUint32()
    local doId = dgi:readUint32()

    local requestedFields = {}
    local count = dgi:readUint16()
    for _ = 1, count, 1 do
        table.insert(requestedFields, dgi:readString())
    end

    local success, body = retrieveObject(participant, doId)
    if not success then
        -- Reply with an error
        local dg = datagram:new()
        dg:addServerHeader(sender, DATABASE_ID, DBSERVER_GET_STORED_VALUES_RESP)
        dg:addUint32(context)
        dg:addUint32(doId)
        dg:addUint16(#requestedFields)
        for _, field in ipairs(requestedFields) do
            dg:addString(field)
        end
        dg:addUint8(1) -- error code
        participant:routeDatagram(dg)
        return
    end

    local data = json.decode(body)
    local packedFieldData = {}
    local dcClass = dcFile:getClassByName(data.objectName)
    local packer = dcpacker:new()

    if data.objectName == "Account" then
        -- CarsClient only use ACCOUNT_AV_SET, so let's set that up
        local avSet = {data.playerId, data.racecarId, data.statusId}
        local packedDg = datagram:new()
        if packer:packField(dcClass:getFieldByName("ACCOUNT_AV_SET"), packedDg, avSet) then
            local packedDgi = datagramiterator.new(packedDg)
            packedFieldData["ACCOUNT_AV_SET"] = packedDgi:readRemainder()
        else
            participant:error("ACCOUNT_AV_SET has failed to pack!")
            -- Reply with an error
            local dg = datagram:new()
            dg:addServerHeader(sender, DATABASE_ID, DBSERVER_GET_STORED_VALUES_RESP)
            dg:addUint32(context)
            dg:addUint32(doId)
            dg:addUint16(#requestedFields)
            for _, field in ipairs(requestedFields) do
                dg:addString(field)
            end
            dg:addUint8(1) -- error code
            participant:routeDatagram(dg)
            return
        end
        goto finish
    elseif data.objectName == "DistributedCarPlayer" or data.objectName == "DistributedRaceCar" then
        -- Use carData for data
        data = data.carData
    end


    for _, field in ipairs(requestedFields) do
        local dcField = dcClass:getFieldByName(field)
        local fieldData
        if field == "setDNA" then
            -- Setup CarDNA struct
            fieldData = {{
                data.carName,
                data.carNumber,
                data.logoBackgroundId,
                data.logoBackgroundColor,
                data.logoFontId,
                data.logoFontColor,
                data.gender,
                data.careerType,
                data.chassisType,
                data.color,
                data.eyeColor,
                data.wheel,
                data.tire,
                data.detailingId,
                data.profileBackgroundId,
                data.stretches[1],
                data.decalSlots,
                data.addonItemList,
                data.costumeId
            }}
        else
            if Field2Api[field] ~= nil then
                fieldData = {data[Field2Api[field]]}
                if fieldData == {nil} then
                    participant:warn(string.format("\"%s\" is missing in API response, returning default value", field))
                    packedFieldData[field] = dcField:getDefaultValue()
                    goto continue
                end
            else
                participant:warn(string.format("\"%s\" is not in Field2Api, returning default value", field))
                packedFieldData[field] = dcField:getDefaultValue()
                goto continue
            end
        end
        local packedDg = datagram:new()
        if packer:packField(dcField, packedDg, fieldData) then
            local packedDgi = datagramiterator.new(packedDg)
            packedFieldData[field] = packedDgi:readRemainder()
        else
            participant:warn(string.format("\"%s\" has failed to pack!", field))
        end
    ::continue::
    end

    ::finish::
    packer:delete()

    -- Send a response:
    local dg = datagram:new()
    dg:addServerHeader(sender, DATABASE_ID, DBSERVER_GET_STORED_VALUES_RESP)
    dg:addUint32(context)
    dg:addUint32(doId)
    dg:addUint16(#requestedFields)
    for _, field in ipairs(requestedFields) do
        dg:addString(field)
    end
    dg:addUint8(0) -- error code

    for _, field in ipairs(requestedFields) do
        if packedFieldData[field] ~= nil then
            dg:addString(packedFieldData[field])
            dg:addBool(true) -- found
        else
            dg:addString("")
            dg:addBool(false) -- found
        end
    end
    participant:routeDatagram(dg)
end

function handleSetStoredValues(participant, dgi)
    local doId = dgi:readUint32()

    local count = dgi:readUint16()
    local packedFields = {}
    for _ = 1, count, 1 do
        packedFields[dgi:readString()] = dgi:readString()
    end

    -- Get the object just so we'll know what we're dealing with.
    local success, body = retrieveObject(participant, doId)
    if not success then
        participant:error(string.format("SetStoredValues: Can't get object for ID: %d", doId))
        return
    end

    local data = json.decode(body)
    local dcClass = dcFile:getClassByName(data.objectName)

    local unpacker = dcpacker:new()
    local Api2Value = {}
    for field, packedValue in pairs(packedFields) do
        local dcField = dcClass:getFieldByName(field)
        local value = unpacker:unpackField(dcField, packedValue)
        if dcField:isAtomic() then
            value = value[1]
        end
        if Field2Api[field] ~= nil then
            Api2Value[Field2Api[field]] = value
        else
            participant:warn(string.format("SetStoredValues: %s is not in Field2Api, ignoring.", field))
        end
    end

    unpacker:delete()
    if Api2Value ~= {} then
        participant:debug(string.format("Sending update to %s(%d): %s", data.objectName, doId, inspect(Api2Value)))
        updateObject(participant, doId, Api2Value)
    end
end
