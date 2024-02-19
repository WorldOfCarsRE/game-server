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

DATABASE_OBJECT_TYPE_ACCOUNT = 1
DATABASE_OBJECT_TYPE_AVATAR  = 2
DATABASE_OBJECT_TYPE_RACECAR = 3
DATABASE_OBJECT_TYPE_CAR_STATUS = 4

-- Internal message types
STATESERVER_OBJECT_UPDATE_FIELD = 2004
STATESERVER_OBJECT_DELETE_RAM = 2007

local inspect = require('inspect')

-- From https://stackoverflow.com/a/22831842
function string.starts(String,Start)
    return string.sub(String,1,string.len(Start))==Start
end

-- From https://stackoverflow.com/a/2421746
function string.upperFirst(str)
    return (string.gsub(str, "^%l", string.upper))
end

function readAccountBridge()
    local json = require("json")
    local io = require("io")

    -- TODO: Custom path.
    f, err = io.open("../otpd/databases/accounts.json", "r")
    if err then
        print("CarsClient: Returning empty table for account bridge")
        return {}
    end

    decoder = json.new_decoder(f)
    result, err = decoder:decode()
    f:close()
    assert(not err, err)
    print("CarsClient: Account bridge successfully loaded.")
    return result
end

ACCOUNT_BRIDGE = readAccountBridge()

function saveAccountBridge()
    local json = require("json")
    local io = require("io")

    -- TODO: Custom path.
    f, err = io.open("../otpd/databases/accounts.json", "w")
    assert(not err, err)
    encoder = json.new_encoder(f)
    err = encoder:encode(ACCOUNT_BRIDGE)
    assert(not err, err)
end

WHITELIST = {}
function readWhitelist()
    local io = require("io")
    local f, err = io.open("../assets/chat_whitelist.xml")
    assert(not err, err)
    for line in f:lines() do
        WHITELIST[line] = true
    end
end
readWhitelist()
print("CarsClient: Successfully loaded whitelist.")

-- Converts a hexadecimal string to a string of bytes
-- From: https://smherwig.blogspot.com/2013/05/a-simple-binascii-module-in-ruby-and-lua.html
function unhexlify(s)
    if #s % 2 ~= 0 then
        error('unhexlify: hexstring must contain even number of digits')
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

local http = require('http')

if PRODUCTION_ENABLED then
    API_BASE = 'https://dxd.sunrise.games/carsds/api/internal/'
else
    API_BASE = 'http://localhost/carsds/api/internal/'
end

function retrieveCar(data)
    response, error_message = http.get(API_BASE .. "retrieveCar", {
        query=data,
        headers={
            ["Authorization"]=API_TOKEN
        }
    })

    return response.body
end

function setCarData(data)
    response, error_message = http.post(API_BASE .. "setCarData", {
        body=data,
        headers={
            ["Authorization"]=API_TOKEN
        }
    })

    return response
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
        client:sendDisconnect(CLIENT_DISCONNECT_OVERSIZED_DATAGRAM, string.format("Datagram contains excess data.\n%s", dgi:dumpHex()), true)
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
    if hash ~= CLIENT_HASH then
        client:sendDisconnect(CLIENT_DISCONNECT_BAD_VERSION, string.format("Client DC hash mismatch: client=%d, server=%d", hash, CLIENT_HASH), true)
        return
    end

    local openChat
    local isPaid
    local dislId
    local linkedToParent
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

            local data, err = crypto.decrypt(encryptedData, 'aes-cbc', unhexlify(PLAY_TOKEN_KEY), crypto.RAW_DATA, iv)
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
            local accountType = jsonData.accountType
            linkedToParent = jsonData.LinkedToParent

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
        if WANT_MEMBERSHIP then
            isPaid = true
        else
            isPaid = false
        end
        dislId = 1
        linkedToParent = false
    end

    local accountId = ACCOUNT_BRIDGE[playToken]
    if accountId ~= nil then
        -- Query the account object
        function queryLoginResponse(doId, success, fields)
            if not success then
                client:sendDisconnect(CLIENT_DISCONNECT_ACCOUNT_ERROR, "The Account object was unable to be queried.", true)
                return
            end

            client:setDatabaseValues(accountId, "Account", {
                LAST_LOGIN = os.date("%a %b %d %H:%M:%S %Y"),
            })

            loginAccount(client, fields, accountId, playToken, openChat, isPaid, dislId, linkedToParent, false)
        end
        client:getDatabaseValues(accountId, "Account", {"ACCOUNT_AV_SET"}, queryLoginResponse)
    else
        -- Create a new Account object
        local account = {
            -- The rest of the values are defined in the dc file.
            CREATED = os.date("%a %b %d %H:%M:%S %Y"),
            LAST_LOGIN = os.date("%a %b %d %H:%M:%S %Y"),
        }

        function createAccountResponse(accountId)
            if accountId == 0 then
                client:sendDisconnect(CLIENT_DISCONNECT_ACCOUNT_ERROR, "The Account object was unable to be created.", false)
                return
            end

            -- Store the account into the bridge
            ACCOUNT_BRIDGE[playToken] = accountId
            saveAccountBridge()

            account.ACCOUNT_AV_SET = {0, 0, 0}

            client:writeServerEvent("account-created", "CarsClient", string.format("%d", accountId))

            createAvatar(client, account, accountId)
            createRaceCar(client, account, accountId, playToken, openChat, isPaid, dislId, linkedToParent)
        end
        client:createDatabaseObject("Account", account, DATABASE_OBJECT_TYPE_ACCOUNT, createAccountResponse)
    end
end

function createAvatar(client, account, accountId)
    function createAvatarResponse(avatarId)
        if avatarId == 0 then
            client:sendDisconnect(CLIENT_DISCONNECT_ACCOUNT_ERROR, "The DistributedCarPlayer object was unable to be created.", false)
            return
        end

        client:writeServerEvent("avatar-created", "CarsClient", string.format("%d", avatarId))

        account.ACCOUNT_AV_SET[1] = avatarId

        client:setDatabaseValues(accountId, "Account", {
            ACCOUNT_AV_SET = account.ACCOUNT_AV_SET,
        })
    end

    -- Create a new DistributedCarPlayer object
    local avatar = {
        -- The rest of the values are defined in the dc file.
        setDISLid = {accountId},
    }

    client:createDatabaseObject("DistributedCarPlayer", avatar, DATABASE_OBJECT_TYPE_AVATAR, createAvatarResponse)
end

function createRaceCar(client, account, accountId, playToken, openChat, isPaid, dislId, linkedToParent)
    function createRaceCarResponse(racecarId)
        if racecarId == 0 then
            client:sendDisconnect(CLIENT_DISCONNECT_ACCOUNT_ERROR, "The DistributedRaceCar object was unable to be created.", false)
            return
        end

        account.ACCOUNT_AV_SET[2] = racecarId

        client:setDatabaseValues(accountId, "Account", {
            ACCOUNT_AV_SET = account.ACCOUNT_AV_SET,
        })

        -- Link account id with AMF car object:
        -- setCarData({playToken, {
        --    dislId = accountId,
         --    playerId =  playerId,
        --    racecarId = racecarId
        -- }})

        loginAccount(client, account, accountId, playToken, openChat, isPaid, dislId, linkedToParent, true)

        client:writeServerEvent("racecar-created", "CarsClient", string.format("%d", racecarId))
    end

    -- Create a new DistributedRaceCar object
    client:createDatabaseObject("DistributedRaceCar", {}, DATABASE_OBJECT_TYPE_RACECAR, createRaceCarResponse)
end

function loginAccount(client, account, accountId, playToken, openChat, isPaid, dislId, linkedToParent, firstLogin)
    -- TODO: Eject logged in accounts.

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
    userTable.openChat = openChat
    client:userTable(userTable)

    -- Log the event
    client:writeServerEvent("account-login", "CarsClient", string.format("%d", accountId))

    -- Prepare the login response.
    local avatarId = userTable.avatars[1]
    local racecarId = userTable.avatars[2]

    if firstLogin then
        local json = require("json")
        local car = json.decode(retrieveCar("playToken=" .. playToken))

        local dna = {
            car.carData.carDna.carName,
            car.carData.carDna.carNumber,
            car.carData.carDna.logoBackgroundId,
            car.carData.carDna.logoBackgroundColor,
            car.carData.carDna.logoFontId,
            car.carData.carDna.logoFontColor,
            car.carData.carDna.gender,
            car.carData.carDna.careerType,
            car.carData.carDna.chassis,
            car.carData.carDna.color,
            car.carData.carDna.eyeColor,
            car.carData.carDna.wheel,
            car.carData.carDna.tire,
            car.carData.carDna.detailing,
            car.carData.carDna.profileBackgroundId,
            car.carData.carDna.stretches,
            car.carData.carDna.decalSlots,
            car.carData.carDna.onAddons,
            car.carData.carDna.costumeId
        }

        client:setDatabaseValues(avatarId, "DistributedCarPlayer", {setDNA = {dna}})
        client:setDatabaseValues(racecarId, "DistributedRaceCar", {setDNA = {dna}})
    end

    local resp = datagram:new()
    resp:addUint16(CLIENT_LOGIN_CARS_RESP)
    resp:addUint8(0) -- Return code
    resp:addString("All Ok") -- errorString
    resp:addUint32(avatarId) -- avatarId
    resp:addUint32(dislId) -- accountId
    resp:addString(playToken) -- playToken
    resp:addUint8(1) -- accountNameApproved
    resp:addString('YES') -- openChatEnabled
    resp:addString('YES') -- createFriendsWithChat
    resp:addString('YES') -- chatCodeCreationRule

    if isPaid then
        resp:addString("FULL") -- access
    else
        resp:addString("VELVET") -- access
    end

    if openChat then
        resp:addString("YES") -- WhiteListResponse
    else
        resp:addString("NO") -- WhiteListResponse
    end

    -- Dispatch the response to the client.
    client:sendDatagram(resp)

    -- Activate DistributedCarPlayer & other owned objects
    userTable.avatarId = avatarId
    client:userTable(userTable)

    client:setChannel(accountId, avatarId)

    local setAccess = 1
    if userTable.isPaid then
        setAccess = 2
    end

    local playerFields = {
        setAccess = {setAccess},
        setTelemetry = {0, 0, 0, 0, 0, 0, 0, 0},
        setPhysics = {{}, {}, {}, {}, {}},
        setState = {0},
        setAfk = {0},
        setDISLname = {playToken},
        setCars = {1, {racecarId}},
    }

    client:sendActivateObject(avatarId, "DistributedCarPlayer", playerFields)

    client:objectSetOwner(avatarId, true)
end

function handleAddInterest(client, dgi)
    local handle = dgi:readInt16()
    local context = dgi:readUint32()
    local parent = dgi:readUint32()
    local zones = {}
    table.insert(zones, dgi:readUint32())
    client:handleAddInterest(handle, context, parent, zones)
end

function clearAvatar(client)
    local userTable = client:userTable()

    if userTable.avatarId == nil then
        return
    end

    client:removeSessionObject(userTable.avatarId)
    client:unsubscribePuppetChannel(userTable.avatarId, 1)

    dg = datagram:new()
    client:addServerHeader(dg, userTable.avatarId, STATESERVER_OBJECT_DELETE_RAM)
    dg:addUint32(userTable.avatarId)
    client:routeDatagram(dg)

    client:clearPostRemoves()

    -- Undeclare all friends.
    client:undeclareAllObjects()

    userTable.avatarId = nil
    userTable.friendsList = nil
    client:userTable(userTable)

    client:setChannel(userTable.accountId, 0)

end

function handleAddOwnership(client, doId, parent, zone, dc, dgi)
    local userTable = client:userTable()
    local accountId = userTable.accountId
    local avatarId = userTable.avatarId
    if doId ~= avatarId then
        client:warn(string.format("Got AddOwnership for object %d, our avatarId is %d", doId, avatarId))
        return
    end

    client:addSessionObject(doId)
    client:subscribePuppetChannel(avatarId, 1)

    -- Store name for SpeedChat+
    -- local name = dgi:readString()
    -- userTable.avatarName = name
    -- client:userTable(userTable)

    local remainder = dgi:readRemainder()

    client:writeServerEvent("selected-avatar", "CarsClient", string.format("%d|%d", accountId, avatarId))

    local resp = datagram:new()
    resp:addUint16(CLIENT_CREATE_OBJECT_REQUIRED_OTHER_OWNER_RESP)
    resp:addUint16(dc) -- dclassId
    resp:addUint32(doId) -- doId
    resp:addUint32(parent) -- parentId
    resp:addUint32(zone) -- zoneId
    -- resp:addString(name) -- setName
    resp:addData(remainder)
    client:sendDatagram(resp)
end

function filterWhitelist(message)
    local modifications = {}
    local wordsToSub = {}
    local offset = 0
    -- Match any character except spaces.
    for word in string.gmatch(message, "[^%s]*") do
        -- Strip out punctuations just for checking with the whitelist.
        local strippedWord = string.gsub(word, "[.,?!]", "")
        if word ~= "" and WHITELIST[string.lower(strippedWord)] ~= true then
            table.insert(modifications, {offset, offset + string.len(word) - 1})
            table.insert(wordsToSub, word)
        end
        if word ~= "" then
            offset = offset + string.len(word) + 1
        end
    end
    local cleanMessage = message

    for _, word in ipairs(wordsToSub) do
        cleanMessage = string.gsub(cleanMessage, word, string.rep('*', string.len(word)), 1)
    end

    return cleanMessage, modifications
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

    local shouldFilterMessage = true
    if userTable.friendsList ~= nil then
        if avatarId == userTable.avatarId then
            -- That's us.  Don't filter from whitelist
            -- if one of our friends is a true friend
            for i, v in ipairs(userTable.friendsList) do
                if userTable.friendsList[i][2] == 1 then
                    shouldFilterMessage = false
                    break
                end
            end
        else
            -- That's a different person.  Check if that person
            -- is a true friend:
            for i, v in ipairs(userTable.friendsList) do
                if userTable.friendsList[i][1] == avatarId and userTable.friendsList[i][2] == 1 then
                    shouldFilterMessage = false
                    break
                end
            end
        end
    end

    if shouldFilterMessage then
        message, modifications = filterWhitelist(message)
    end

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
    -- Check friends list if what we're sending this too is a true friend:
    if userTable.friendsList ~= nil then
        for i, v in ipairs(userTable.friendsList) do
            if v[1] == doId and v[2] == 1 then
                -- Send unfiltered message
                cleanMessage, modifications = message, {}
            end
        end
    end

    local dg = datagram:new()
    -- We set the sender field to the doId instead of our channel to make sure
    -- we can receive the broadcast.
    dg:addServerHeader(doId, doId, STATESERVER_OBJECT_UPDATE_FIELD)
    dg:addUint32(doId)
    client:packFieldToDatagram(dg, "DistributedCarPlayer", "setTalkWhisper", {avatarId, accountId, avatarName, cleanMessage, modifications, 0}, true)
    client:routeDatagram(dg)
end
