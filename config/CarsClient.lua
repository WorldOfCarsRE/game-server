-- Client messages
CLIENT_GO_GET_LOST_RESP = 4 -- Sent by the server when it is dropping the connection deliberately.

CLIENT_LOGIN_CARS = 114
CLIENT_LOGIN_CARS_RESP = 115

CLIENT_SET_INTEREST = 97
CLIENT_REMOVE_INTEREST = 99

CLIENT_CREATE_OBJECT_REQUIRED_OTHER_RESP = 35
CLIENT_CREATE_OBJECT_REQUIRED_OTHER_OWNER_RESP = 36
CLIENT_CREATE_OBJECT_REQUIRED_RESP = 34

CLIENT_HEART_BEAT = 52

CLIENT_SYSTEM_ALERT = 78
CLIENT_SYSTEM_ALERT_WITHRESP = 123

CLIENT_SET_LOCATION = 102

CLIENT_OBJECT_UPDATE_FIELD = 24
CLIENT_OBJECT_DISABLE_RESP = 25

CLIENT_DONE_SET_ZONE_RESP = 48

CLIENT_DISCONNECT_GENERIC                = 1
CLIENT_DISCONNECT_RELOGIN                = 100
CLIENT_DISCONNECT_OVERSIZED_DATAGRAM     = 106
CLIENT_DISCONNECT_NO_HELLO               = 107
CLIENT_DISCONNECT_CHAT_AUTH_ERROR        = 120
CLIENT_DISCONNECT_ACCOUNT_ERROR          = 122
CLIENT_DISCONNECT_NO_HEARTBEAT           = 345
CLIENT_DISCONNECT_INVALID_MSGTYPE        = 108
CLIENT_DISCONNECT_TRUNCATED_DATAGRAM     = 109
CLIENT_DISCONNECT_ANONYMOUS_VIOLATION    = 113
CLIENT_DISCONNECT_FORBIDDEN_INTEREST     = 115
CLIENT_DISCONNECT_MISSING_OBJECT         = 117
CLIENT_DISCONNECT_FORBIDDEN_FIELD        = 118
CLIENT_DISCONNECT_FORBIDDEN_RELOCATE     = 119
CLIENT_DISCONNECT_BAD_VERSION            = 125
CLIENT_DISCONNECT_FIELD_CONSTRAINT       = 127
CLIENT_DISCONNECT_SESSION_OBJECT_DELETED = 153

LOGOUT_REASON_ACCOUNT_DISABLED = 152

DATABASE_OBJECT_TYPE_ACCOUNT = 1
DATABASE_OBJECT_TYPE_AVATAR  = 2
DATABASE_OBJECT_TYPE_RACECAR = 3
DATABASE_OBJECT_TYPE_CAR_STATUS = 4

-- Internal message types
STATESERVER_OBJECT_UPDATE_FIELD = 2004
STATESERVER_OBJECT_DELETE_RAM = 2007

CLIENTAGENT_EJECT = 3004

CENTRAL_LOGGER_REQUEST = 15000

local inspect = require("inspect")

-- Load the TalkFilter
dofile("TalkFilter.lua")

-- Converts a hexadecimal string to a string of bytes
-- From: https://smherwig.blogspot.com/2013/05/a-simple-binascii-module-in-ruby-and-lua.html
function unhexlify(s)
    if #s % 2 ~= 0 then
        error("unhexlify: hexstring must contain even number of digits")
    end
    local a = {}
    for i=1,#s,2 do
        local hs = string.sub(s, i, i+1)
        local code = tonumber(hs, 16)
        if not code then
            error(string.format("unhexlify: '%s' is not avalid hex number", hs))
        end
        table.insert(a, string.char(code))
    end
    return table.concat(a)
end

-- Load the configuration varables (see config.example.lua)
dofile("config.lua")

local API_BASE

local http = require("http")

if PRODUCTION_ENABLED then
    API_BASE = "https://dxd.sunrise.games/carsds/api/internal/"
else
    API_BASE = "http://localhost/carsds/api/internal/"
end

avatarSpeedChatPlusStates = {}

-- TODO: These three functions should be moved to their own
-- Lua role.
function retrieveAccount(data)
    -- TODO: Retries
    local response, error_message = http.get(API_BASE .. "retrieveAccount", {
        query=data,
        headers={
            ["Authorization"]=API_TOKEN
        }
    })

    if error_message then
        print(string.format("CarsClient: retrieveAccount returned an error! \"%s\"", error_message))
        return "{}"
    end
    if response.status_code ~= 200 then
        print(string.format("CarsClient: retrieveAccount returned %d!, \"%s\"", response.status_code, response.body))
        return "{}"
    end
    return response.body
end

function retrieveCar(client, data)
    local connAttempts = 0

    while (connAttempts < 3) do
        local response, error_message = http.get(API_BASE .. "retrieveCar", {
            query=data,
            headers={
                ["User-Agent"]=USER_AGENT,
                ["Authorization"]=API_TOKEN
            }
        })

        if error_message then
            print(string.format("CarsClient: retrieveCar returned an error! \"%s\"", error_message))
            connAttempts = connAttempts + 1
            goto retry
        end

        if response.status_code ~= 200 then
            print(string.format("CarsClient: retrieveCar returned %d!, \"%s\"", response.status_code, response.body))
            connAttempts = connAttempts + 1
            goto retry
        end

        do
            -- If we're here, then we can return the response body.
            print(response.body)
            return response.body
        end

        -- retry goto to iterate again if we failed to retrieve our car data.
        ::retry::
    end

    -- If we're here, then we failed to get valid car data. Disconnect here
    client:sendDisconnect(CLIENT_DISCONNECT_ACCOUNT_ERROR, "Failed to retrieveCar.", false)
end

function setCarData(client, playToken, data)
    local request = {playToken = playToken, fieldData = data}
    local json = require("json")
    local result, err = json.encode(request)

    if err then
        print(err)
        client:sendDisconnect(CLIENT_DISCONNECT_ACCOUNT_ERROR, "Failed to encode JSON data for setCarData.", false)
        return
    end

    local connAttempts = 0
    while (connAttempts < 3) do
        local response, error_message = http.post(API_BASE .. "setCarData", {
            body=result,
            headers={
                ["Authorization"]=API_TOKEN,
                ["User-Agent"]=USER_AGENT,
                ["Content-Type"]="application/json"
            }
        })

        if error_message then
            print(string.format("CarsClient: setCarData returned an error! \"%s\"", error_message))
            connAttempts = connAttempts + 1
            goto retry
        end

        if response.status_code ~= 200 then
            print(string.format("CarsClient: setCarData returned %d!, \"%s\"", response.status_code, response.body))
            connAttempts = connAttempts + 1
            goto retry
        end

        do
            -- If we're here, then we can return the response.
            return response
        end

        -- retry goto to iterate again if we failed to set our car data.
        ::retry::
    end

    -- If we're here, then we failed to set our car data. Disconnect here
    client:sendDisconnect(CLIENT_DISCONNECT_ACCOUNT_ERROR, "Failed to setCarData.", false)
end

function setCarFields(client, playToken, data)
    local request = {playToken = playToken, fieldData = data}
    local json = require("json")
    local result, err = json.encode(request)

    if err then
        print(err)
        client:sendDisconnect(CLIENT_DISCONNECT_ACCOUNT_ERROR, "Failed to encode JSON data for setCarFields.", false)
        return
    end

    local connAttempts = 0
    while (connAttempts < 3) do
        local response, error_message = http.post(API_BASE .. "setCarFields", {
            body=result,
            headers={
                ["Authorization"]=API_TOKEN,
                ["User-Agent"]=USER_AGENT,
                ["Content-Type"]="application/json"
            }
        })

        if error_message then
            print(string.format("CarsClient: setCarFields returned an error! \"%s\"", error_message))
            connAttempts = connAttempts + 1
            goto retry
        end

        if response.status_code ~= 200 then
            print(string.format("CarsClient: setCarFields returned %d!, \"%s\"", response.status_code, response.body))
            connAttempts = connAttempts + 1
            goto retry
        end

        do
            -- If we're here, then we can return the response.
            return response
        end

        -- retry goto to iterate again if we failed to set our car fields.
        ::retry::
    end

    -- If we're here, then we failed to set our car fields. Disconnect here
    client:sendDisconnect(CLIENT_DISCONNECT_ACCOUNT_ERROR, "Failed to setCarFields.", false)
end

function handleDatagram(client, msgType, dgi)
    -- Internal datagrams
    client:warn(string.format("Received unknown server msgtype %d", msgType))
end

function receiveDatagram(client, dgi)
    -- Client received datagrams
    msgType = dgi:readUint16()

    if msgType == CLIENT_HEART_BEAT then
        client:handleHeartbeat()
    elseif msgType == CLIENT_DISCONNECT then
        client:handleDisconnect()
    elseif msgType == CLIENT_LOGIN_CARS then
        handleLogin(client, dgi)
    -- We have reached the only message types unauthenticated clients can use.
    elseif not client:authenticated() then
        client:sendDisconnect(CLIENT_DISCONNECT_GENERIC, "First datagram is not CLIENT_LOGIN_CARS", true)
    elseif msgType == CLIENT_SET_INTEREST then
        handleAddInterest(client, dgi)
    elseif msgType == CLIENT_REMOVE_INTEREST then
        client:handleRemoveInterest(dgi)
    elseif msgType == CLIENT_OBJECT_UPDATE_FIELD then
        client:handleUpdateField(dgi)
    elseif msgType == CLIENT_SET_LOCATION then
        client:setLocation(dgi)
    else
        client:sendDisconnect(CLIENT_DISCONNECT_GENERIC, string.format("Unknown message type: %d", msgType), true)
    end

    if dgi:getRemainingSize() ~= 0 then
        client:sendDisconnect(CLIENT_DISCONNECT_OVERSIZED_DATAGRAM, string.format("Datagram contains excess data.\n%s", tostring(dgi)), true)
    end
end

function handleLogin(client, dgi)
    local playToken = dgi:readString()
    local version = dgi:readString()
    local hash = dgi:readUint32()
    local tokenType = dgi:readInt32()
    dgi:readString()

    if client:authenticated() then
        client:sendDisconnect(CLIENT_DISCONNECT_RELOGIN, "Authenticated client tried to login twice!", true)
        return
    end

    -- Check if version and hash matches
    if version ~= SERVER_VERSION then
        client:sendDisconnect(CLIENT_DISCONNECT_BAD_VERSION, string.format("Client version mismatch: client=%s, server=%s", version, SERVER_VERSION), true)
        return
    end
    -- Doesn't seem dcFile.getHash() matches the client.
    -- We'll just hardcode the stock WOC client hashVal.
    -- This shouldn't change as we won't be adding new content anyways.
    if hash ~= 46329213 then
        client:sendDisconnect(CLIENT_DISCONNECT_BAD_VERSION, string.format("Client DC hash mismatch: client=%d, server=%d", hash, CLIENT_HASH), true)
        return
    end

    local speedChatPlus
    local openChat
    local isPaid
    local dislId
    local linkedToParent
    local accountDisabled
    if PRODUCTION_ENABLED then
        local json = require("json")
        local crypto = require("crypto")
        local ok, err = pcall(function()
            local decodedToken, err = crypto.base64_decode(playToken)
            if err then
                error(err)
                return
            end
            local encrypted, err = json.decode(decodedToken)
            if err then
                error(err)
                return
            end
            local encryptedData, err = crypto.base64_decode(encrypted.data)
            if err then
                error(err)
                return
            end
            local iv, err = crypto.base64_decode(encrypted.iv)
            if err then
                error(err)
                return
            end

            local data, err = crypto.decrypt(encryptedData, "aes-cbc", unhexlify(PLAY_TOKEN_KEY), crypto.RAW_DATA, iv)
            if err then
                error(err)
                return
            end
            local jsonData, err = json.decode(data)
            if err then
                error(err)
                return
            end

            -- Retrieve data from the API response.
            playToken = jsonData.playToken
            if tonumber(jsonData.OpenChat) == 1 then
                openChat = true
            else
                openChat = false
            end

            if tonumber(jsonData.Member) == 1 then
                isPaid = true
            else
                isPaid = false
            end

            local timestamp = jsonData.Timestamp
            dislId = tonumber(jsonData.dislId)
            accountType = jsonData.accountType
            linkedToParent = jsonData.LinkedToParent

            if tonumber(jsonData.SpeedChatPlus) == 1 then
                speedChatPlus = true
            else
                speedChatPlus = false
            end

            if tonumber(jsonData.Banned) == 1 or tonumber(jsonData.Terminated) == 1 then
                accountDisabled = true
            else
                accountDisabled = false
            end

            if WANT_TOKEN_EXPIRATIONS and timestamp < os.time() then
                client:sendDisconnect(CLIENT_DISCONNECT_ACCOUNT_ERROR, "Token has expired.", true)
                return
            end
        end)

        if not ok then
            -- Bad play token
            client:warn(string.format("CarsClient: Error when decrypting play token: %s", err))
            client:sendDisconnect(CLIENT_DISCONNECT_ACCOUNT_ERROR, "Invalid play token", true)
            return
        end
        -- TODO: Send discord webhook.
    else
        -- Production is not enabled
        -- We need these dummy values
        openChat = false
        if WANT_OPEN_CHAT then
            openChat = true
        end
        isPaid = false
        if WANT_MEMBERSHIP then
            isPaid = true
        end
        dislId = 1
        linkedToParent = false
        accountType = "Administrator"
        speedChatPlus = false
        if WANT_SPEEDCHAT_PLUS then
            speedChatPlus = true
        end
        accountDisabled = false
    end

    local json = require("json")
    local account = json.decode(retrieveAccount("userName=" .. playToken))
    local accountId = account._id
    -- Query the account object
    client:getDatabaseValues(accountId, "Account", {"ACCOUNT_AV_SET"}, function (doId, success, fields)
        if not success then
            client:sendDisconnect(CLIENT_DISCONNECT_ACCOUNT_ERROR, "The Account object was unable to be queried.", true)
            return
        end

        client:setDatabaseValues(accountId, "Account", {
            LAST_LOGIN = os.date("%a %b %d %H:%M:%S %Y"),
        })

        loginAccount(client, fields, accountId, playToken, openChat, isPaid, dislId, linkedToParent, accountType, speedChatPlus, accountDisabled)
    end)
end

function loginAccount(client, account, accountId, playToken, openChat, isPaid, dislId, linkedToParent, accountType, speedChatPlus, accountDisabled)
    if accountDisabled then
        client:sendDisconnect(LOGOUT_REASON_ACCOUNT_DISABLED, "There has been a reported violation of our Terms of Use connected to this account. For safety purposes, we have placed a temporary hold on the account.  For more details, please review the messages sent to the email address associated with this account.", false)
        return
    end

    -- Eject other client if already logged in.
    local ejectDg = datagram:new()
    client:addServerHeaderWithAccountId(ejectDg, accountId, CLIENTAGENT_EJECT)
    ejectDg:addUint16(CLIENT_DISCONNECT_RELOGIN)
    ejectDg:addString("You have been disconnected because someone else just logged in using your account on another computer.")
    client:routeDatagram(ejectDg)

    -- Subscribe to our puppet channel.
    client:subscribePuppetChannel(accountId, 3)

    -- Set our channel containing our account id
    client:setChannel(accountId, 0)

    client:authenticated(true)

    -- Store the account id and avatar list into our client's user table:
    local userTable = client:userTable()
    userTable.accountId = accountId
    userTable.avatars = account.ACCOUNT_AV_SET
    userTable.playToken = playToken
    userTable.isPaid = isPaid
    -- TODO: A way to toggle SpeedChat Plus, re-enable when ready
    userTable.speedChatPlus = true -- speedChatPlus
    userTable.openChat = openChat
    userTable.accountType = accountType
    client:userTable(userTable)

    -- Log the event
    client:writeServerEvent("account-login", "CarsClient", string.format("%d", accountId))

    -- Prepare the login response.
    local avatarId = userTable.avatars[1]
    local racecarId = userTable.avatars[2]
    local statusId = userTable.avatars[3]

    local json = require("json")
    local account = json.decode(retrieveAccount("userName=" .. playToken))
    local car = json.decode(retrieveCar(client, "playToken=" .. playToken))

    -- Store name for SpeedChat+
    -- By default the name is formatted like "Wreckless,Spinna,roader" so we format it to normal "Wreckless Spinnaroader".
    local name = ""
    local count = 0

    for part in string.gmatch(car.carData.carDna.carName, "([^,]+)") do
        if count == 1 then
            name = name .. " " .. part
        else
            name = name .. part
        end

        count = count + 1
    end

    userTable.avatarName = name
    client:userTable(userTable)

    local resp = datagram:new()
    resp:addUint16(CLIENT_LOGIN_CARS_RESP)
    resp:addUint8(0) -- Return code
    resp:addString("All Ok") -- errorString
    resp:addUint32(avatarId) -- avatarId
    resp:addUint32(dislId) -- accountId
    resp:addString(playToken) -- playToken
    resp:addUint8(1) -- accountNameApproved

    if openChat then
        resp:addString("YES") -- openChatEnabled
    else
        resp:addString("NO") -- openChatEnabled
    end

    resp:addString("YES") -- createFriendsWithChat
    resp:addString("YES") -- chatCodeCreationRule

    if isPaid then
        resp:addString("FULL") -- access
    else
        resp:addString("VELVET") -- access
    end

    if speedChatPlus then
        resp:addString("YES") -- WhiteListResponse
    else
        resp:addString("NO") -- WhiteListResponse
    end

    -- Dispatch the response to the client.
    client:sendDatagram(resp)

    -- Activate DistributedCarPlayer & other owned objects
    userTable.avatarId = avatarId
    userTable.racecarId = racecarId
    client:userTable(userTable)

    client:setChannel(accountId, avatarId)
    client:subscribePuppetChannel(avatarId, 1)

    -- TODO: Re-enable membership after we implement sponsors
    local setAccess = 1
    -- if userTable.isPaid then
        -- setAccess = 2
    -- end

    local chatLevel = 0
    if userTable.speedChatPlus then
        chatLevel = 1
    end

    local playerFields = {
        setAccess = {setAccess},
        setTelemetry = {0, 0, 0, 0, 0, 0, 0, 0},
        setPhysics = {{}, {}, {}, {}, {}},
        setState = {0},
        setAfk = {0},
        setDISLname = {playToken},
        setCars = {1, {racecarId}},
        setChatLevel = {chatLevel},
    }

    local function isPuppet(puppetId)
        if puppetId ~= nil then
            if puppetId > 0 then
                return true
            end
        end
        return false
    end

    if isPuppet(account.puppet) then
        playerFields.setPuppetId = {account.puppet}
        client:sendActivateObject(avatarId, "DistributedCarPuppet", playerFields)
    else
        client:sendActivateObject(avatarId, "DistributedCarPlayer", playerFields)
    end
    client:objectSetOwner(avatarId, true)

    client:sendActivateObject(racecarId, "DistributedRaceCar", {})
    client:objectSetOwner(racecarId, true)

    client:sendActivateObject(statusId, "CarPlayerStatus", {})
    client:objectSetOwner(statusId, true)

    avatarSpeedChatPlusStates[avatarId] = userTable.speedChatPlus
end

function handleAddInterest(client, dgi)
    local handle = dgi:readInt16()
    local context = dgi:readUint32()
    local parent = dgi:readUint32()
    local zones = {}
    table.insert(zones, dgi:readUint32())
    client:handleAddInterest(handle, context, parent, zones)
end

function handleAddOwnership(client, doId, parent, zone, dc, dgi)
    local userTable = client:userTable()
    local accountId = userTable.accountId
    local avatarId = userTable.avatarId
    local racecarId = userTable.racecarId
    if doId == avatarId then
        client:writeServerEvent("selected-avatar", "CarsClient", string.format("%d|%d", accountId, avatarId))
    end

    client:addSessionObject(doId)

    local requiredFields = {}
    local ownRequiredFields = {}
    local dbFields = {}

    local dcClass = dcFile:getClass(dc)
    client:debug(string.format("Handling ownership generation for class \"%s\"", dcClass:getName()))

    local numFields = dcClass:getNumFields()
    for i = 0, numFields - 1, 1 do
        local dcField = dcClass:getField(i)
        if dcField:hasKeyword("required") then
            table.insert(requiredFields, dcField)
        end
        if dcField:hasKeyword("ownrequired") then
            table.insert(ownRequiredFields, dcField)
        end
        if dcField:hasKeyword("db") then
            table.insert(dbFields, dcField:getName())
        end
    end

    -- TODO: Handle if the object isn't in database.
    client:getDatabaseValues(doId, dcClass:getName(), dbFields, function (_, success, databaseFields)
        local requiredField2Value = {}
        local otherField2Value = {}
        local packer = dcpacker:new()

        -- First, we unpack all the required fields:
        for _, requiredField in ipairs(requiredFields) do
            local value = packer:unpackField(requiredField, dgi)
            requiredField2Value[requiredField] = value
        end

        -- Then the other fields, if any:
        if dgi:getRemainingSize() > 0 then
            local numFields = dgi:readUint16()
            for i = 1, numFields, 1 do
                local fieldId = dgi:readUint16()
                local dcField = dcFile:getFieldByIndex(fieldId)
                local value = packer:unpackField(dcField, dgi)
                otherField2Value[dcField:getName()] = value
            end
        end

        -- Now, populate the ownrequired fields with data.
        local generateData = datagram:new()
        for _, ownRequiredField in ipairs(ownRequiredFields) do
            local value = requiredField2Value[ownRequiredField]
            local otherValue = otherField2Value[ownRequiredField:getName()]
            if value ~= nil then
                client:debug(string.format("Packing found ownrequired field \"%s\": %s", ownRequiredField:getName(), inspect(value)))
                packer:packField(ownRequiredField, generateData, value)
            elseif otherValue ~= nil then
                client:debug(string.format("Packing found ownrequired field from OTHER \"%s\": %s", ownRequiredField:getName(), inspect(otherValue)))
                packer:packField(ownRequiredField, generateData, otherValue)
                otherField2Value[ownRequiredField:getName()] = nil
            elseif databaseFields[ownRequiredField:getName()] ~= nil then
                client:debug(string.format("Packing found ownrequired field from database \"%s\": %s", ownRequiredField:getName(), inspect(databaseFields[ownRequiredField:getName()])))
                packer:packField(ownRequiredField, generateData, databaseFields[ownRequiredField:getName()])
            else
                -- TODO:  This might need fetching some stuff from the API server, because not
                -- everything is set to "required", even though the owner generate message needs them.
                client:warn(string.format("No value for ownrequired field \"%s\".  Adding default value", ownRequiredField:getName()))
                generateData:addData(ownRequiredField:getDefaultValue())
            end
        end

        -- Add leftover OTHER fields
        local numOtherFields = 0
        local otherData = datagram:new()
        for fieldName, value in pairs(otherField2Value) do
            numOtherFields = numOtherFields + 1
            local dcField = dcClass:getFieldByName(fieldName)
            otherData:addUint16(dcField:getNumber())
            packer:packField(dcField, otherData, value)
        end

        packer:delete()

        local resp = datagram:new()
        resp:addUint16(CLIENT_CREATE_OBJECT_REQUIRED_OTHER_OWNER_RESP)
        resp:addUint16(dc) -- dclassId
        resp:addUint32(doId) -- doId
        resp:addUint32(parent) -- parentId
        resp:addUint32(zone) -- zoneId
        -- resp:addString(name) -- setName
        resp:addDatagram(generateData)
        if numOtherFields > 0 then
            resp:addUint16(numOtherFields)
            resp:addDatagram(otherData)
        end
        client:sendDatagram(resp)
    end)
end

-- setTalk from client
function handleClientDistributedCarPlayer_setTalk(client, doId, fieldId, data)
    -- The data is safe to use, as the ranges has already been
    -- verified by the server prior to calling this function.

    local userTable = client:userTable()
    local accountId = userTable.accountId
    local avatarId = userTable.avatarId
    local avatarName = userTable.avatarName

    -- All other data are blank values, except for chat.
    local message = data[4] --chat

    local dg = datagram:new()
    -- We set the sender field to the doId instead of our channel to make sure
    -- we can receive the broadcast.
    dg:addServerHeader(doId, doId, STATESERVER_OBJECT_UPDATE_FIELD)
    dg:addUint32(doId)
    client:packFieldToDatagram(dg, "DistributedCarPlayer", "setTalk", {avatarId, accountId, avatarName, message, {}, 0}, true)
    client:routeDatagram(dg)
end

-- setTalk from server
function handleDistributedCarPlayer_setTalk(client, doId, fieldId, data)
    -- The data is safe to use, as the ranges has already been
    -- verified by the server prior to calling this function.

    local userTable = client:userTable()

    local avatarId = data[1]
    local accountId = data[2]
    local avatarName = data[3]
    local message = data[4]
    -- The rest are intentionally left blank.
    local modifications = {}

    -- Special cases
    local filterOverride = true

    -- sender, receiver
    if (avatarSpeedChatPlusStates[avatarId] and userTable.speedChatPlus) then
        filterOverride = false
    end

    message, modifications = filterWhitelist(message, filterOverride)

    local dg = datagram:new()
    dg:addUint16(CLIENT_OBJECT_UPDATE_FIELD)
    dg:addUint32(doId)
    client:packFieldToDatagram(dg, "DistributedCarPlayer", "setTalk", {avatarId, accountId, avatarName, message, modifications, 0}, true)
    client:sendDatagram(dg)
end

function handleClientDistributedCarPlayer_setTalkWhisper(client, doId, fieldId, data)
    -- The data is safe to use, as the ranges has already been
    -- verified by the server prior to calling this function.

    local userTable = client:userTable()
    local accountId = userTable.accountId
    local avatarId = userTable.avatarId
    local avatarName = userTable.avatarName

    -- All other data are blank values, except for chat.
    local message = data[4] --chat

    if message == "" then
        return
    end

    local cleanMessage, modifications = filterWhitelist(message)

    local dg = datagram:new()
    -- We set the sender field to the doId instead of our channel to make sure
    -- we can receive the broadcast.
    dg:addServerHeader(doId, doId, STATESERVER_OBJECT_UPDATE_FIELD)
    dg:addUint32(doId)
    client:packFieldToDatagram(dg, "DistributedCarPlayer", "setTalkWhisper", {avatarId, accountId, avatarName, cleanMessage, modifications, 0}, true)
    client:routeDatagram(dg)
end

-- Make sure these works for puppets as well.
handleClientDistributedCarPuppet_setTalk = handleClientDistributedCarPlayer_setTalk
handleDistributedCarPuppet_setTalk = handleDistributedCarPlayer_setTalk
handleClientDistributedCarPuppet_setTalkWhisper = handleClientDistributedCarPlayer_setTalkWhisper

function getCategoryDescription(category)
    if category == "MODERATION_FOUL_LANGUAGE" then
        return "Foul Language"
    elseif category == "MODERATION_PERSONAL_INFO" then
        return "Personal Information"
    elseif category == "MODERATION_RUDE_BEHAVIOR" then
        return "Rude Behavior"
    elseif category == "MODERATION_BAD_NAME" then
        return "Bad Name"
    end
    return "Unknown Category"
end

-- sendMessage from client
function handleClientCentralLogger_sendMessage(client, doId, fieldId, data)
    -- The data is safe to use, as the ranges has already been
    -- verified by the server prior to calling this function.
    local category = data[1]
    local eventString = data[2]
    local targetDISLId = data[3]
    local targetAvId = data[4]

    local toLog = eventString .. "|" .. string.format("%d", targetDISLId) .. "|" .. string.format("%d", targetAvId)
    client:writeServerEvent(category, "CentralLogger", toLog)

    if PRODUCTION_ENABLED then
        -- Send a request to our Discord service for moderation.
        dg = datagram:new()
        client:addServerHeader(dg, CENTRAL_LOGGER_REQUEST, CENTRAL_LOGGER_REQUEST)
        dg:addString(REPORTS_WEBHOOK_URL) -- webhookUrl
        dg:addString(eventString) -- message
        dg:addString(getCategoryDescription(category)) -- category
        dg:addUint32(targetAvId) -- targetAvId
        client:routeDatagram(dg)
    end
end
