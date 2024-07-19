OTP_DO_ID_PLAYER_FRIENDS_MANAGER = 4687

STATESERVER_OBJECT_UPDATE_FIELD = 2004

INVRESP_ACCEPTED = 5
INVRESP_DECLINED = 1
INVRESP_ALREADYFRIEND = 4

-- For verifying that their friend is online.
DBSS_OBJECT_GET_ACTIVATED = 2207
DBSS_OBJECT_GET_ACTIVATED_RESP = 2208

-- Load the configuration varables (see config.example.lua)
dofile("config.lua")

local inspect = require('inspect')

invitesByInviterId = {} -- inviterId: invite
invitesByInviteeId = {} -- inviteeId: invite


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
    inviterData.carData.carDna.carName = formatCarName(inviterData.carData.carDna.carName)
    inviteeData.carData.carDna.carName = formatCarName(inviteeData.carData.carDna.carName)
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

function handleDatagram(participant, msgType, dgi)
    if msgType == STATESERVER_OBJECT_UPDATE_FIELD then
        if dgi:readUint32() == OTP_DO_ID_PLAYER_FRIENDS_MANAGER then
            participant:handleUpdateField(dgi, "PlayerFriendsManager")
        end
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

    local json = require("json")
    local inviterData = json.decode(retrieveCar(string.format("identifier=%d", senderId)))
    local inviteeData = json.decode(retrieveCar(string.format("identifier=%d", otherPlayerId)))

    local invite = newInviteTable(senderId, inviterData, otherPlayerId, inviteeData)
    invitesByInviterId[senderId] = invite
    invitesByInviteeId[otherPlayerId] = invite

    participant:sendUpdateToAccountId(otherPlayerId, OTP_DO_ID_PLAYER_FRIENDS_MANAGER,
            "PlayerFriendsManager", "invitationFrom", {senderId, inviterData.carData.carDna.carName})
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
