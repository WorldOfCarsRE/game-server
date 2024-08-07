CENTRAL_LOGGER_REQUEST = 15000
CENTRAL_LOGGER_REQUEST_RESP = 15001

SERVER_TYPE = "World of Cars Online"

local http = require("http")
local json = require("json")

function sendToDiscord(hook, color, name, message, fields)
    local embed = {
          {
              ["color"] = color,
              ["title"] = "**".. name .."**",
              ["description"] = message,
              ["fields"] = fields
          }
      }

    http.post(hook, {
        body=json.encode({username = name, embeds = embed}),
        headers={
            ["Content-Type"]="application/json"
        }
    })
end

function init(participant)
    participant:subscribeChannel(CENTRAL_LOGGER_REQUEST)
end

function handleDatagram(participant, msgType, dgi)
    if msgType == CENTRAL_LOGGER_REQUEST then
        handleCentralLoggerRequest(dgi)
    else
        participant:warning(string.format("Got unknown message type: %d", msgType))
    end
end

function handleCentralLoggerRequest(participant, dgi)
    local webhookUrl = dgi:readString()
    local message = dgi:readString()
    local category = dgi:readString()
    local targetAvId = dgi:readUint32()

    sendToDiscord(webhookUrl, 1127128, "Reports", "Someone is reporting to us!", {
        {
            name = "Message",
            value = message,
            inline = true
        },
        {
            name = "Category",
            value = category,
            inline = true
        },
        {
            name = "Target Avatar Id",
            value = targetAvId,
            inline = true
        },
        {
            name = "Sender Avatar Id",
            value = participant:getAvatarIdFromSender(),
            inline = true
        },
        {
            name = "Server Type",
            value = SERVER_TYPE,
            inline = true
        }
    })
end
