OTP_DO_ID_PLAYER_FRIENDS_MANAGER = 4687

STATESERVER_OBJECT_UPDATE_FIELD = 2004

INVRESP_ACCEPTED = 5
INVRESP_DECLINED = 1
INVRESP_ALREADYFRIEND = 4

MAX_FRIENDS = 300

FRIENDMANAGER_ACCOUNT_ONLINE  = 10000
FRIENDMANAGER_ACCOUNT_OFFLINE = 10001

-- For verifying that their friend is online.
DBSS_OBJECT_GET_ACTIVATED      = 2207
DBSS_OBJECT_GET_ACTIVATED_RESP = 2208

-- For declaring friends.
CLIENTAGENT_DECLARE_OBJECT   = 3010
CLIENTAGENT_UNDECLARE_OBJECT = 3011

-- Avatar class to declare.
AVATAR_CLASS = dcFile:getClassByName("DistributedCarPlayer"):getNumber()

-- Load the configuration varables (see config.example.lua)
dofile("config.lua")

local inspect = require('inspect')

invitesByInviterId = {} -- inviterId: invite
invitesByInviteeId = {} -- inviteeId: invite

CONTEXT = 0
DBSS_QUERY_MAP = {}

-- Load the TalkFilter
dofile("TalkFilter.lua")

function init(participant)
    participant:subscribeChannel(OTP_DO_ID_PLAYER_FRIENDS_MANAGER)
end

function formatCarName(carName)
    -- By default the name is formatted like "Wreckless,Spinna,roader" so we format it to normal "Wreckless Spinnaroader".
    local name = ""
    local count = 0

    for part in string.gmatch(carName, "([^,]+)") do
        if count == 1 then
            name = name .. " " .. part
        else
            name = name .. part
        end

        count = count + 1
    end
    return name
end

function newInviteTable(inviterId, inviterData, inviteeId, inviteeData)
    return {
        inviterId = inviterId,
        inviterData = inviterData,
        inviteeId = inviteeId,
        inviteeData = inviteeData
    }
end

local http = require('http')

if PRODUCTION_ENABLED then
    API_BASE = 'https://dxd.sunrise.games/carsds/api/internal/'
else
    API_BASE = 'http://localhost/carsds/api/internal/'
end

-- TODO: These two functions should be moved to their own
-- Lua role.
function retrieveCar(data)
    response, error_message = http.get(API_BASE .. "retrieveCar", {
        query=data,
        headers={
            ["Authorization"]=API_TOKEN
        }
    })

    return response.body
end

function setCarData(playToken, data)
    local request = {playToken = playToken, fieldData = data}
    local json = require("json")
    local result, err = json.encode(request)
    if err then
        print(err)
        return
    end
    response, error_message = http.post(API_BASE .. "setCarData", {
        body=result,
        headers={
            ["Authorization"]=API_TOKEN,
            ["Content-Type"]="application/json"
        }
    })

    return response
end

function declareFriend(participant, avatarId, friendId)
    -- Make sure that these are AVATAR ids, not ACCOUNT ids.
    local dg = datagram:new()
    participant:addServerHeaderWithAvatarId(dg, avatarId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER, CLIENTAGENT_DECLARE_OBJECT)
    participant:addUint32(friendId)
    participant:addUint16(AVATAR_CLASS)
    participant:routeDatagram(dg)
end

function undeclareFriend(participant, avatarId, friendId)
    -- Make sure that these are AVATAR ids, not ACCOUNT ids.
    local dg = datagram:new()
    participant:addServerHeaderWithAvatarId(dg, avatarId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER, CLIENTAGENT_UNDECLARE_OBJECT)
    participant:addUint32(friendId)
    participant:routeDatagram(dg)
end

function queryDBSS(participant, avatarId, callback)
    DBSS_QUERY_MAP[CONTEXT] = callback

    local dg = datagram:new()
    dg:addServerHeader(avatarId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER, DBSS_OBJECT_GET_ACTIVATED)
    dg:addUint32(CONTEXT)
    dg:addUint32(avatarId)
    participant:routeDatagram(dg)

    CONTEXT = CONTEXT + 1
end

function handleDatagram(participant, msgType, dgi)
    if msgType == STATESERVER_OBJECT_UPDATE_FIELD then
        if dgi:readUint32() == OTP_DO_ID_PLAYER_FRIENDS_MANAGER then
            participant:handleUpdateField(dgi, "PlayerFriendsManager")
        end
    elseif msgType == FRIENDMANAGER_ACCOUNT_ONLINE then
        handleOnline(participant, dgi:readUint32())
    elseif msgType == FRIENDMANAGER_ACCOUNT_OFFLINE then
        handleOffline(participant, dgi:readUint32())
    elseif msgType == DBSS_OBJECT_GET_ACTIVATED_RESP then
        local context = dgi:readUint32()
        local doId = dgi:readUint32()
        local activated = dgi:readBool()

        local callback = DBSS_QUERY_MAP[context]
        if callback ~= nil then
            callback(doId, activated)
            DBSS_QUERY_MAP[context] = nil
        else
            participant:warn(string.format("Got GET_ACTIVATED_RESP with unknown context: %d", context))
        end
    end
end

function handleOnline(participant, accountId)
    participant:debug(string.format("handleOnline - %d", accountId))
    local json = require("json")

    local account = json.decode(retrieveCar(string.format("identifier=%d", accountId)))
    -- Tell this account's friends that it went online.
    local friendInfo = {
        formatCarName(account.carData.carDna.carName), -- avatarName
        account.playerId, -- avatarId
        account.ownerAccount, -- playerName
        1, -- onlineYesNo
        -- Most of these values appears to be unused.
        0, -- openChatEnabledYesNo
        0, -- openChatFriendshipYesNo
        0, -- wlChatEnabledYesNo
        "", -- location
        "", -- sublocation
        0  -- timestamp
    }

    for _, friendId in ipairs(account.friends) do
        participant:sendUpdateToAccountId(friendId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER,
            "PlayerFriendsManager", "updatePlayerFriend", {accountId, friendInfo, 0})

        local dg = datagram:new()
        participant:addServerHeaderWithAccountId(dg, friendId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER, CLIENTAGENT_DECLARE_OBJECT)
        dg:addUint32(account.playerId)
        dg:addUint16(AVATAR_CLASS)
        participant:routeDatagram(dg)
    end

    -- Now to send the friend list over to the just logged in account.
    for _, friendId in ipairs(account.friends) do
        local friendAccount = json.decode(retrieveCar(string.format("identifier=%d", friendId)))

        local dg = datagram:new()
        participant:addServerHeaderWithAccountId(dg, accountId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER, CLIENTAGENT_DECLARE_OBJECT)
        dg:addUint32(friendAccount.playerId)
        dg:addUint16(AVATAR_CLASS)
        participant:routeDatagram(dg)

        -- Check if this account's avatar is online or not.
        queryDBSS(participant, friendAccount.playerId, function (doId, activated)
            participant:debug(string.format("Is friend %d online? %s", friendAccount.playerId, tostring(activated)))
            friendInfo = {
                formatCarName(friendAccount.carData.carDna.carName), -- avatarName
                friendAccount.playerId, -- avatarId
                friendAccount.ownerAccount, -- playerName
                activated, -- onlineYesNo
                -- Most of these values appears to be unused.
                0, -- openChatEnabledYesNo
                0, -- openChatFriendshipYesNo
                0, -- wlChatEnabledYesNo
                "", -- location
                "", -- sublocation
                0  -- timestamp
            }
            participant:sendUpdateToAccountId(accountId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER,
                "PlayerFriendsManager", "updatePlayerFriend", {friendId, friendInfo, 0})
        end)
    end
end

function handleOffline(participant, accountId)
    participant:debug(string.format("handleOffline - %d", accountId))
    local json = require("json")

    local account = json.decode(retrieveCar(string.format("identifier=%d", accountId)))
    -- Tell this account's friends that it went offline.
    local friendInfo = {
        formatCarName(account.carData.carDna.carName), -- avatarName
        account.playerId, -- avatarId
        account.ownerAccount, -- playerName
        0, -- onlineYesNo
        -- Most of these values appears to be unused.
        0, -- openChatEnabledYesNo
        0, -- openChatFriendshipYesNo
        0, -- wlChatEnabledYesNo
        "", -- location
        "", -- sublocation
        0  -- timestamp
    }

    for _, friendId in ipairs(account.friends) do
        participant:sendUpdateToAccountId(friendId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER,
            "PlayerFriendsManager", "updatePlayerFriend", {accountId, friendInfo, 0})
    end
end

function handlePlayerFriendsManager_requestInvite(participant, fieldId, data)
    local senderId = participant:getAccountIdFromSender()
    local otherPlayerId = data[2]
    local secretYesNo = data[3]
    participant:debug(string.format("requestInvite - %d - %d - %d", senderId, otherPlayerId, secretYesNo))

    if senderId == otherPlayerId then
        return
    end

    if invitesByInviteeId[senderId] ~= nil then
        makeFriends(participant, invitesByInviteeId[senderId])
        return
    end

    local json = require("json")
    local inviterData = json.decode(retrieveCar(string.format("identifier=%d", senderId)))
    local inviteeData = json.decode(retrieveCar(string.format("identifier=%d", otherPlayerId)))

    local invite = newInviteTable(senderId, inviterData, otherPlayerId, inviteeData)
    invitesByInviterId[senderId] = invite
    invitesByInviteeId[otherPlayerId] = invite

    participant:sendUpdateToAccountId(otherPlayerId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER,
            "PlayerFriendsManager", "invitationFrom", {senderId, formatCarName(inviterData.carData.carDna.carName)})
end

function handlePlayerFriendsManager_requestDecline(participant, fieldId, data)
    local senderId = participant:getAccountIdFromSender()
    local otherPlayerId = data[2]
    participant:debug(string.format("requestDecline - %d - %d", senderId, otherPlayerId))

    -- Cleanup
    invitesByInviterId[senderId] = nil
    invitesByInviteeId[senderId] = nil
    invitesByInviterId[otherPlayerId] = nil
    invitesByInviteeId[otherPlayerId] = nil

    participant:sendUpdateToAccountId(otherPlayerId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER,
            "PlayerFriendsManager", "invitationResponse", {senderId, INVRESP_DECLINED, 0})
end

function makeFriends(participant, invite)
    participant:debug(string.format("makeFriends - %d - %d", invite.inviterId, invite.inviteeId))

    if invite.inviterData.friends == nil then
        invite.inviterData.friends = {}
    end
    if invite.inviteeData.friends == nil then
        invite.inviteeData.friends = {}
    end

    local status = INVRESP_ACCEPTED
    if #invite.inviterData.friends >= MAX_FRIENDS then
        status = INVRESP_DECLINED
    end

    if status == INVRESP_ACCEPTED then
        table.insert(invite.inviterData.friends, invite.inviteeId)
        setCarData(invite.inviterData.ownerAccount, {friends = invite.inviterData.friends})

        local friendInfo = {
            formatCarName(invite.inviteeData.carData.carDna.carName), -- avatarName
            invite.inviteeData.playerId, -- avatarId
            invite.inviteeData.ownerAccount, -- playerName
            1, -- onlineYesNo
            -- Most of these values appears to be unused.
            0, -- openChatEnabledYesNo
            0, -- openChatFriendshipYesNo
            0, -- wlChatEnabledYesNo
            "", -- location
            "", -- sublocation
            0  -- timestamp
        }

        participant:sendUpdateToAccountId(invite.inviterId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER,
                "PlayerFriendsManager", "updatePlayerFriend", {invite.inviteeId, friendInfo, 0})
    end

    status = INVRESP_ACCEPTED
    if #invite.inviteeData.friends >= MAX_FRIENDS then
        status = INVRESP_DECLINED
    end

    if status == INVRESP_ACCEPTED then
        table.insert(invite.inviteeData.friends, invite.inviterId)
        setCarData(invite.inviteeData.ownerAccount, {friends = invite.inviteeData.friends})

        local friendInfo = {
            formatCarName(invite.inviterData.carData.carDna.carName), -- avatarName
            invite.inviterData.playerId, -- avatarId
            invite.inviterData.ownerAccount, -- playerName
            1, -- onlineYesNo
            -- Most of these values appears to be unused.
            0, -- openChatEnabledYesNo
            0, -- openChatFriendshipYesNo
            0, -- wlChatEnabledYesNo
            "", -- location
            "", -- sublocation
            0  -- timestamp
        }

        participant:sendUpdateToAccountId(invite.inviteeId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER,
                "PlayerFriendsManager", "updatePlayerFriend", {invite.inviterId, friendInfo, 0})
    end

    participant:sendUpdateToAccountId(invite.inviterId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER,
            "PlayerFriendsManager", "invitationResponse", {invite.inviteeId, status, 0})

end

function handlePlayerFriendsManager_setTalkAccount(participant, fieldId, data)
    local senderId = participant:getAccountIdFromSender()
    local otherAccountId = data[1]
    participant:debug(string.format("setTalkAccount - %d - %d", senderId, otherAccountId))

    -- All other data are blank values, except for chat.
    local message = data[4] --chat

    if message == "" then
        return
    end

    local cleanMessage, modifications = filterWhitelist(message, false)

    participant:sendUpdateToAccountId(otherAccountId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER,
            "PlayerFriendsManager", "setTalkAccount", {otherAccountId, senderId, avatarName, cleanMessage, modifications, 0})
end
