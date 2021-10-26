from pandac.PandaModules import *
from . import CatalogItem
from ai import ToontownGlobals

bannedPhrases = [11009]

class CatalogChatItem(CatalogItem.CatalogItem):

    def makeNewItem(self, customIndex):
        self.customIndex = customIndex
        CatalogItem.CatalogItem.makeNewItem(self)

    def getPurchaseLimit(self):
        return 1

    def reachedPurchaseLimit(self, avatar):
        if self in avatar.onOrder or self in avatar.mailboxContents or self in avatar.onGiftOrder or self in avatar.awardMailboxContents or self in avatar.onAwardOrder:
            return 1
        return avatar.customMessages.count(self.customIndex) != 0

    def recordPurchase(self, avatar, optional):
        if avatar.customMessages.count(self.customIndex) != 0:
            return ToontownGlobals.P_ReachedPurchaseLimit
        if len(avatar.customMessages) >= ToontownGlobals.MaxCustomMessages:
            if optional >= 0 and optional < len(avatar.customMessages):
                del avatar.customMessages[optional]
            if len(avatar.customMessages) >= ToontownGlobals.MaxCustomMessages:
                return ToontownGlobals.P_NoRoomForItem
        avatar.customMessages.append(self.customIndex)
        avatar.d_setCustomMessages(avatar.customMessages)
        return ToontownGlobals.P_ItemAvailable

    def output(self, store = -1):
        return 'CatalogChatItem(%s%s)' % (self.customIndex, self.formatOptionalData(store))

    def compareTo(self, other):
        return self.customIndex - other.customIndex

    def getHashContents(self):
        return self.customIndex

    def getBasePrice(self):
        if self.customIndex >= 10000:
            return 150
        return 100

    def decodeDatagram(self, di, versionNumber, store):
        CatalogItem.CatalogItem.decodeDatagram(self, di, versionNumber, store)
        self.customIndex = di.getUint16()
        text = OTPLocalizer.CustomSCStrings[self.customIndex]

    def encodeDatagram(self, dg, store):
        CatalogItem.CatalogItem.encodeDatagram(self, dg, store)
        dg.addUint16(self.customIndex)

def getChatRange(fromIndex, toIndex, *otherRanges):
    chatList = []
    froms = [fromIndex]
    tos = [toIndex]
    i = 0
    while i < len(otherRanges):
        froms.append(otherRanges[i])
        tos.append(otherRanges[i + 1])
        i += 2

    for chatId in ToontownGlobals.CustomSCStrings.keys():
        for fromIndex, toIndex in zip(froms, tos):
            if chatId >= fromIndex and chatId <= toIndex and chatId not in bannedPhrases:
                chatList.append(CatalogChatItem(chatId))

    return chatList
