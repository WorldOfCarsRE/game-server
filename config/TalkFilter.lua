-- From https://stackoverflow.com/a/22831842
function string.starts(String,Start)
    return string.sub(String,1,string.len(Start))==Start
end

-- https://gist.github.com/VADemon/afb10dbb0d10d99aeb21449752da6285
function regexEscape(str)
    return string.gsub(str, "[%(%)%.%%%+%-%*%?%[%^%$%]]", "%%%1")
end

string.replace = function (str, this, that)
    return string.gsub(str, regexEscape(this), string.gsub(that, "%%", "%%%%")) -- only % needs to be escaped for 'that'
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
print("TalkFilter: Successfully loaded whitelist.")

SPEEDCHAT = {}
function readChatPhrases()
    local io = require("io")
    local f, err = io.open("../assets/speedchat.txt")
    assert(not err, err)
    for line in f:lines() do
        SPEEDCHAT[line] = true
    end
end
readChatPhrases()
print("TalkFilter: Successfully loaded SpeedChat phrases.")

function filterWhitelist(message, filterOverride)
    if SPEEDCHAT[message] then
        return message, {}
    end

    local modifications = {}
    local wordsToSub = {}
    local offset = 0

    if filterOverride then
        local cleanMessage = "*"
        table.insert(modifications, {0, 0})
        return cleanMessage, modifications
      end

    -- Match any character except spaces.
    for word in string.gmatch(message, "[^%s]*") do
        -- Strip out punctuations just for checking with the whitelist.
        local strippedWord = string.gsub(word, "[.,?!]", "")
        if filterOverride == true or word ~= "" and WHITELIST[string.lower(strippedWord)] ~= true then
            table.insert(modifications, {offset, offset + string.len(word) - 1})
            table.insert(wordsToSub, word)
        end
        if word ~= "" then
            offset = offset + string.len(word) + 1
        end
    end
    local cleanMessage = message

    for _, word in ipairs(wordsToSub) do
        cleanMessage = string.replace(cleanMessage, word, string.rep("*", string.len(word)))
    end

    return cleanMessage, modifications
end
