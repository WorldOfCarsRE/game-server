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

local function replaceModifiedText(str, modifications)
    local cleanMessage = str
    for _, modification in ipairs(modifications) do
        local length = modification[2] - modification[1] + 1
        cleanMessage = string.sub(cleanMessage, 0, modification[1]) .. string.rep("*", length) .. string.sub(cleanMessage, modification[1] + 1 + length)
    end
    return cleanMessage
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

function isWordOnWhitelist(word)
    -- Test without stripping out the punctuations first
    if WHITELIST[string.lower(word)] then
        return true
    end
    -- Now try with puncutations stripped out
    return WHITELIST[string.lower(string.gsub(word, "[.,?!]", ""))]
end

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

    local function stripLeadingAndTrailingPunctuation(word, reversed)
        -- Disney just stripped punctuation from the start and end of the word. This allows words with punctuation to be in the whitelist.
        local pattern = "[.,?!]+"
        local strippedWord = word
        local matchStart, matchEnd = string.find(strippedWord, pattern)

        -- Strip leading characters.
        if matchStart == 1 then
            strippedWord = string.sub(strippedWord, matchEnd + 1)
        end

        -- We will reverse the word and call ourself again if we haven't already, to make checking for trailing characters easier.
        local reversedWord = string.reverse(strippedWord)

        if not reversed then
            return stripLeadingAndTrailingPunctuation(reversedWord, true)
        end

        -- Return the reversed word. This will actually be the normal word since we only get here in the reversed call.
        return reversedWord
    end

    local function isWordOnWhitelist(word)
        local wordToFind = string.lower(word)

        -- If the word is already on the whitelist, we can return immediately.
        if WHITELIST[wordToFind] then
            return true
        end

        wordToFind = stripLeadingAndTrailingPunctuation(wordToFind, false)

        -- Now return whether the word is in the whitelist.
        return WHITELIST[wordToFind]
    end

    -- Match any character except spaces.
    for word in string.gmatch(message, "[^%s]*") do
        if filterOverride == true or word ~= "" and isWordOnWhitelist(word) ~= true then
            table.insert(modifications, {offset, offset + string.len(word) - 1})
            table.insert(wordsToSub, word)
        end
        if word ~= "" then
            offset = offset + string.len(word) + 1
        end
    end
    local cleanMessage = replaceModifiedText(message, modifications)

    return cleanMessage, modifications
end
