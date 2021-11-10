from ai.DistributedObjectAI import DistributedObjectAI
from ai.DistributedSmoothNodeAI import DistributedSmoothNodeAI
from otp.util import getPuppetChannel
from panda3d.core import Datagram, DatagramIterator

from typing import NamedTuple, List, Dict
from ai.battle.BattleGlobals import *
from ai.globals import HoodGlobals
from ai.fishing.FishBase import FishBase
from ai.fishing.FishCollectionEnum import *
from ai.toon.Inventory import Inventory

from ai.toon import ToonDNA
from ai import ToontownGlobals
from ai.catalog.CatalogItemList import CatalogItemList
from ai.catalog import CatalogAccessoryItem
from ai.catalog import CatalogItem
import time

from direct.task import Task

class DistributedAvatarAI(DistributedSmoothNodeAI):
    def __init__(self, air):
        DistributedSmoothNodeAI.__init__(self, air)

        self.name = 'Toon'

    def setName(self, name):
        self.name = name

    def getName(self):
        return self.name

    def b_setName(self, name):
        self.setName(name)
        self.d_setName(name)

    def d_setName(self, name):
        self.sendUpdate('setName', [name])

class FriendEntry(NamedTuple):
    doId: int
    trueFriend: bool

class DistributedPlayerAI(DistributedAvatarAI):
    def __init__(self, air):
        DistributedAvatarAI.__init__(self, air)

        self.accountName = ''
        self.DISLid = 0
        self.access = 0
        self.friendsList: List[FriendEntry] = []

    def delete(self):
        self.stopToonUp()
        self.sendUpdate('arrivedOnDistrict', [0])
        self.air.decrementPopulation()
        DistributedAvatarAI.delete(self)

    def setAccountName(self, name):
        self.accountName = name

    def getAccountName(self):
        return self.accountName

    def setFriendsList(self, friendsList):
        self.friendsList = friendsList

    def getFriendsList(self):
        return self.friendsList

    def d_setFriendsList(self, friendsList: List[FriendEntry]):
        self.sendUpdate('setFriendsList', [friendsList])

    def setDISLid(self, DISLid):
        self.DISLid = DISLid

    def getDISLid(self):
        return self.DISLid

    def getPreviousAccess(self):
        # AccessFull = 2
        return 2

    def setAccess(self, access):
        self.access = access

    def getAccess(self):
        return self.access

    def getAsGM(self):
        return False

    def extendFriendsList(self, friendId: int, trueFriend: bool):
        for i, entry in enumerate(self.friendsList):
            if entry[0] == friendId:
                self.friendsList[i] = FriendEntry(friendId, trueFriend)
                return

        self.friendsList.append(FriendEntry(friendId, trueFriend))

    def d_setSystemMessage(self, aboutId: int, chatString: ''):
        self.sendUpdate('setSystemMessage', [aboutId, chatString])

MAX_NPC_FRIENDS_FLAG = 1 << 15

class DistributedToonAI(DistributedPlayerAI):
    STREET_INTEREST_HANDLE = (1 << 15) + 1

    def __init__(self, air):
        DistributedPlayerAI.__init__(self, air)

        self.hp = 15
        self.maxHp = 15
        self.maxMoney = 40
        self.money = 0
        self.bankMoney = 0
        self.maxBankMoney = 1000
        self.petTrickPhrases: List[int] = []
        self.clothesTopsList: List[int] = []
        self.clothesBottomsList: List[int] = []
        self.maxClothes = 10
        self.trackAccess = [0, 0, 0, 0, 1, 1, 0]
        self.trackBonusLevel = [-1, -1, -1, -1, -1, -1, -1]
        self.experience = Experience()
        self.inventory = Inventory()
        self.fishCollection = FishCollection()
        self.fishTank = FishTank()
        self.maxNPCFriends = 8
        self.npcFriends: Dict[int, int] = {}
        self.pinkSlips = 0
        self.battleId = 0
        self.defaultZone = 0
        self.lastHood = 0
        self.hoodsVisited = []
        self.fishingTrophies = []
        self.catalogNotify = ToontownGlobals.NoItems
        self.mailboxNotify = ToontownGlobals.NoItems
        self.catalogScheduleCurrentWeek = 0
        self.catalogScheduleNextTime = 0
        self.monthlyCatalog = CatalogItemList()
        self.weeklyCatalog = CatalogItemList()
        self.backCatalog = CatalogItemList()
        self.quests = []
        self.houseId = 0
        self.onOrder = CatalogItemList(store = CatalogItem.Customization | CatalogItem.DeliveryDate)
        self.onGiftOrder = CatalogItemList(store = CatalogItem.Customization | CatalogItem.DeliveryDate)
        self.mailboxContents = CatalogItemList(store = CatalogItem.Customization)
        self.awardMailboxContents = CatalogItemList(store = CatalogItem.Customization)
        self.onAwardOrder = CatalogItemList(store = CatalogItem.Customization | CatalogItem.DeliveryDate)
        self.customMessages = []
        self.ghostMode = 0
        self.numMailItems = 0
        self.awardNotify = ToontownGlobals.NoItems
        self.dna = ToonDNA.ToonDNA()
        self.maxAccessories = 0
        self.hatList = []
        self.glassesList = []
        self.backpackList = []
        self.shoesList = []
        self.hat = (0, 0, 0)
        self.glasses = (0, 0, 0)
        self.backpack = (0, 0, 0)
        self.shoes = (0, 0, 0)
        self.nametagStyle = 0
        self.emoteAccess = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    def setDNAString(self, dnaString):
        self.dna.makeFromNetString(dnaString)

    def b_setDNAString(self, dnaString):
        self.d_setDNAString(dnaString)
        self.setDNAString(dnaString)

    def d_setDNAString(self, dnaString):
        self.sendUpdate('setDNAString', [dnaString])

    def getDNAString(self):
        return self.dna.makeNetString()

    def getStyle(self):
        return self.dna

    def getGM(self):
        return False

    def setMaxBankMoney(self, money):
        self.maxBankMoney = money

    def getMaxBankMoney(self):
        return self.maxBankMoney

    def setBankMoney(self, money):
        self.bankMoney = money

    def getBankMoney(self):
        return self.bankMoney

    def b_setBankMoney(self, money):
        self.bankMoney = money
        self.sendUpdate('setBankMoney', [money])

    def setMaxMoney(self, maxMoney):
        self.maxMoney = maxMoney

    def getMaxMoney(self):
        return self.maxMoney

    def setMoney(self, money):
        self.money = money

    def getMoney(self):
        return self.money

    def getTotalMoney(self):
        return self.money + self.bankMoney

    def d_setMoney(self, money):
        self.sendUpdate('setMoney', [money])

    def b_setMoney(self, money):
        self.setMoney(money)
        self.d_setMoney(money)

    def takeMoney(self, deltaMoney, useBank=True):
        totalMoney = self.money + (self.bankMoney if useBank else 0)
        if deltaMoney > totalMoney:
            return False

        if useBank and deltaMoney > self.money:
            self.b_setBankMoney(self.bankMoney - (deltaMoney - self.money))
            self.b_setMoney(0)
        else:
            self.b_setMoney(self.money - deltaMoney)
        return True

    def addMoney(self, deltaMoney):
        money = deltaMoney + self.money
        pocketMoney = min(money, self.maxMoney)
        self.b_setMoney(pocketMoney)
        overflowMoney = money - self.maxMoney
        if overflowMoney > 0:
            bankMoney = self.bankMoney + overflowMoney
            self.b_setBankMoney(bankMoney)

    def setMaxHp(self, hp):
        self.maxHp = hp

    def getMaxHp(self):
        return self.maxHp

    def setHp(self, hp):
        self.hp = hp

    def getHp(self):
        return self.hp

    def d_setHp(self, hp):
        self.sendUpdate('setHp', [hp])

    def b_setHp(self, hp):
        self.setHp(hp)
        self.d_setHp(hp)

    def toonUp(self, hpGained, quietly = 0, sendTotal = 1):
        hpGained = min(self.maxHp, hpGained)
        if not quietly:
            self.sendUpdate('toonUp', [hpGained])
        if self.hp + hpGained <= 0:
            self.hp += hpGained
        else:
            self.hp = max(self.hp, 0) + hpGained
        clampedHp = min(self.hp, self.maxHp)
        if sendTotal:
            self.d_setHp(clampedHp)

    def takeDamage(self, hpLost, quietly = 0, sendTotal = 1):
        if not quietly:
            self.sendUpdate('takeDamage', [hpLost])
        if hpLost > 0 and self.hp > 0:
            self.hp = max(self.hp - hpLost, -1)
            messenger.send(self.getGoneSadMessage())
        self.hp = min(self.hp, self.maxHp)
        if sendTotal:
            self.d_setHp(self.hp)

    def getToonUpTaskName(self):
        return self.uniqueName('toonUpTask')

    def startToonUp(self, frequency, amount):
        self.stopToonUp()
        taskMgr.doMethodLater(frequency, self.doToonUpTask,
                              self.getToonUpTaskName(), extraArgs = [amount])

    def stopToonUp(self):
        taskMgr.remove(self.getToonUpTaskName())

    def doToonUpTask(self, amount, task = None):
        self.toonUp(amount)
        if task:
            return task.cont

    @staticmethod
    def getGoneSadMessageForAvId(avId):
        return f'goneSad-{avId}'

    def getGoneSadMessage(self):
        return self.getGoneSadMessageForAvId(self.do_id)

    def getBattleId(self):
        return self.battleId

    def b_setBattleId(self, battleId):
        self.battleId = battleId
        self.sendUpdate('setBattleId', [battleId])

    def setExperience(self, experience):
        self.experience = Experience.fromBytes(experience)
        self.experience.toon = self

    def getExperience(self):
        return self.experience.makeNetString()

    def getMaxCarry(self):
        return 20

    def setTrackAccess(self, trackAccess):
        self.trackAccess = trackAccess

    def getTrackAccess(self):
        return self.trackAccess

    def hasTrackAccess(self, track):
        return self.trackAccess[track] > 0

    def getTrackProgress(self):
        return 0, 0

    def getTrackBonusLevel(self):
        return self.trackBonusLevel

    def propHasOrganicBonus(self, track, level) -> bool:
        return self.trackBonusLevel[track] >= level

    def setInventory(self, inventory):
        self.inventory = Inventory.fromBytes(inventory)
        self.inventory.toon = self

    def getInventory(self):
        return self.inventory.makeNetString()

    def d_setInventory(self, blob):
        self.sendUpdate('setInventory', [blob])

    def setMaxNPCFriends(self, maxNum):
        if maxNum & MAX_NPC_FRIENDS_FLAG:
            self.d_setSosPageFlag(1)
            # Keep other bits.
            maxNum &= MAX_NPC_FRIENDS_FLAG - 1

        self.maxNPCFriends = maxNum

    def getMaxNPCFriends(self):
        return self.maxNPCFriends

    def d_setSosPageFlag(self, flag):
        self.sendUpdate('setSosPageFlag', [flag])

    def getNPCFriendsDict(self):
        return list(self.npcFriends.items())

    def d_setMaxClothes(self, max):
        self.sendUpdate('setMaxClothes', [self.maxClothes])

    def setMaxClothes(self, maxClothes):
        self.maxClothes = maxClothes

    def b_setMaxClothes(self, maxClothes):
        self.setMaxClothes(maxClothes)
        self.d_setMaxClothes(maxClothes)

    def getMaxClothes(self):
        return self.maxClothes

    def isClosetFull(self, extraClothes = 0):
        numClothes = len(self.clothesTopsList) / 4 + len(self.clothesBottomsList) / 2
        return (numClothes + extraClothes >= self.maxClothes)

    def d_setClothesTopsList(self, clothesList):
        self.sendUpdate('setClothesTopsList', [clothesList])

    def setClothesTopsList(self, clothesList):
        self.clothesTopsList = clothesList

    def b_setClothesTopsList(self, clothesList):
        self.setClothesTopsList(clothesList)
        self.d_setClothesTopsList(clothesList)

    def getClothesTopsList(self):
        return self.clothesTopsList

    def addToClothesTopsList(self, topTex, topTexColor,
                                sleeveTex, sleeveTexColor):
        if self.isClosetFull():
            return 0

        index = 0
        for i in range(0, len(self.clothesTopsList), 4):
            if (self.clothesTopsList[i] == topTex and
                self.clothesTopsList[i + 1] == topTexColor and
                self.clothesTopsList[i + 2] == sleeveTex and
                self.clothesTopsList[i + 3] == sleeveTexColor):
                return 0

        self.clothesTopsList.append(topTex)
        self.clothesTopsList.append(topTexColor)
        self.clothesTopsList.append(sleeveTex)
        self.clothesTopsList.append(sleeveTexColor)
        return 1

    def replaceItemInClothesTopsList(self, topTexA, topTexColorA,
                                     sleeveTexA, sleeveTexColorA,
                                     topTexB, topTexColorB,
                                     sleeveTexB, sleeveTexColorB):
        index = 0
        for i in range(0, len(self.clothesTopsList), 4):
            if (self.clothesTopsList[i] == topTexA and
                self.clothesTopsList[i + 1] == topTexColorA and
                self.clothesTopsList[i + 2] == sleeveTexA and
                self.clothesTopsList[i + 3] == sleeveTexColorA):
                self.clothesTopsList[i] = topTexB
                self.clothesTopsList[i + 1] = topTexColorB
                self.clothesTopsList[i + 2] = sleeveTexB
                self.clothesTopsList[i + 3] = sleeveTexColorB
                return 1
        return 0

    def removeItemInClothesTopsList(self, topTex, topTexColor,
                                    sleeveTex, sleeveTexColor):
        listLen = len(self.clothesTopsList)
        if listLen < 4:
            print('Clothes top list is not long enough to delete anything')
            return 0
        index = 0
        for i in range(0, listLen, 4):
            if (self.clothesTopsList[i] == topTex and
                self.clothesTopsList[i + 1] == topTexColor and
                self.clothesTopsList[i + 2] == sleeveTex and
                self.clothesTopsList[i + 3] == sleeveTexColor):
                self.clothesTopsList = self.clothesTopsList[0:i] + self.clothesTopsList[i + 4:listLen]
                return 1
        return 0

    def d_setClothesBottomsList(self, clothesList):
        self.sendUpdate('setClothesBottomsList', [clothesList])

    def setClothesBottomsList(self, clothesList):
        self.clothesBottomsList = clothesList

    def b_setClothesBottomsList(self, clothesList):
        self.setClothesBottomsList(clothesList)
        self.d_setClothesBottomsList(clothesList)

    def getClothesBottomsList(self):
        return self.clothesBottomsList

    def addToClothesBottomsList(self, botTex, botTexColor):
        if self.isClosetFull():
            print('clothes bottoms list is full')
            return 0
        index = 0
        for i in range(0, len(self.clothesBottomsList), 2):
            if (self.clothesBottomsList[i] == botTex and
                self.clothesBottomsList[i + 1] == botTexColor):
                return 0
        self.clothesBottomsList.append(botTex)
        self.clothesBottomsList.append(botTexColor)
        return 1

    def replaceItemInClothesBottomsList(self, botTexA, botTexColorA,
                                        botTexB, botTexColorB):
        index = 0
        for i in range(0, len(self.clothesBottomsList), 2):
            if (self.clothesBottomsList[i] == botTexA and
                self.clothesBottomsList[i + 1] == botTexColorA):
                self.clothesBottomsList[i] = botTexB
                self.clothesBottomsList[i + 1] = botTexColorB
                return 1
        return 0

    def removeItemInClothesBottomsList(self, botTex, botTexColor):
        listLen = len(self.clothesBottomsList)
        if listLen < 2:
            print('Clothes bottoms list is not long enough to delete anything')
            return 0
        index = 0
        for i in range(0, len(self.clothesBottomsList), 2):
            if (self.clothesBottomsList[i] == botTex and
                self.clothesBottomsList[i + 1] == botTexColor):
                self.clothesBottomsList = self.clothesBottomsList[0:i] + self.clothesBottomsList[i + 2:listLen]
                return 1
        return 0

    def getDefaultShard(self):
        return 0

    def setDefaultZone(self, zone: int):
        self.defaultZone = zone

    def d_setDefaultZone(self, zone: int):
        self.sendUpdate('setDefaultZone', [zone])

    def b_setDefaultZone(self, zone: int):
        if zone != self.defaultZone:
            self.setDefaultZone(zone)
            self.d_setDefaultZone(zone)

    def getDefaultZone(self):
        return self.defaultZone

    def getShtickerBook(self):
        return b''

    def getZonesVisited(self):
        return []

    def b_setHoodsVisited(self, hoodsVisited: list):
        self.hoodsVisited = hoodsVisited
        self.d_setHoodsVisited(hoodsVisited)

    def d_setHoodsVisited(self, hoodsVisited: list):
        self.sendUpdate('setHoodsVisited', [hoodsVisited])

    def getHoodsVisited(self):
        return self.hoodsVisited

    def getInterface(self):
        return b''

    def setLastHood(self, hood: int):
        self.lastHood = hood

    def d_setLastHood(self, hood: int):
        self.sendUpdate('setLastHood', [hood])

    def b_setLastHood(self, hood: int):
        if hood != self.lastHood:
            self.setLastHood(hood)
            self.d_setLastHood(hood)

    def getLastHood(self):
        return self.lastHood

    def getTutorialAck(self):
        return 1

    def setClothesTopsList(self, clothesList):
        self.clothesTopsList = clothesList

    def b_setClothesTopsList(self, clothesList):
        self.setClothesTopsList(clothesList)
        self.d_setClothesTopsList(clothesList)

    def getClothesTopsList(self):
        return self.clothesTopsList

    def setClothesBottomsList(self, clothesList):
        self.clothesBottomsList = clothesList

    def b_setClothesBottomsList(self, clothesList):
        self.setClothesBottomsList(clothesList)
        self.d_setClothesBottomsList(clothesList)

    def getClothesBottomsList(self):
        return self.clothesBottomsList

    def d_setMaxAccessories(self, maxAccessories):
        self.sendUpdate('setMaxAccessories', [self.maxAccessories])

    def setMaxAccessories(self, maxAccessories):
        self.maxAccessories = maxAccessories

    def b_setMaxAccessories(self, maxAccessories):
        self.setMaxAccessories(maxAccessories)
        self.d_setMaxAccessories(maxAccessories)

    def checkAccessorySanity(self, accessoryType, idx, textureIdx, colorIdx):
        if idx == 0 and textureIdx == 0 and colorIdx == 0:
            return 1
        if accessoryType == ToonDNA.HAT:
            stylesDict = ToonDNA.HatStyles
            accessoryTypeStr = 'Hat'
        elif accessoryType == ToonDNA.GLASSES:
            stylesDict = ToonDNA.GlassesStyles
            accessoryTypeStr = 'Glasses'
        elif accessoryType == ToonDNA.BACKPACK:
            stylesDict = ToonDNA.BackpackStyles
            accessoryTypeStr = 'Backpack'
        elif accessoryType == ToonDNA.SHOES:
            stylesDict = ToonDNA.ShoesStyles
            accessoryTypeStr = 'Shoes'
        else:
            return 0
        try:
            styleStr = list(stylesDict.keys())[list(stylesDict.values()).index([idx, textureIdx, colorIdx])]
            accessoryItemId = 0
            for itemId in list(CatalogAccessoryItem.AccessoryTypes.keys()):
                if styleStr == CatalogAccessoryItem.AccessoryTypes[itemId][CatalogAccessoryItem.ATString]:
                    accessoryItemId = itemId
                    break

            if accessoryItemId == 0:
                return 0
            #if not simbase.config.GetBool('want-check-accessory-sanity', False):
            return 1
            #accessoryItem = CatalogAccessoryItem.CatalogAccessoryItem(accessoryItemId)
            #result = self.air.catalogManager.isItemReleased(accessoryItem)
            #return result
        except:
            return 0

    def addToAccessoriesList(self, accessoryType, geomIdx, texIdx, colorIdx):
        if self.isTrunkFull():
            return 0
        if accessoryType == ToonDNA.HAT:
            itemList = self.hatList
        elif accessoryType == ToonDNA.GLASSES:
            itemList = self.glassesList
        elif accessoryType == ToonDNA.BACKPACK:
            itemList = self.backpackList
        elif accessoryType == ToonDNA.SHOES:
            itemList = self.shoesList
        else:
            return 0
        index = 0
        for i in range(0, len(itemList), 3):
            if itemList[i] == geomIdx and itemList[i + 1] == texIdx and itemList[i + 2] == colorIdx:
                return 0

        if accessoryType == ToonDNA.HAT:
            self.hatList.append(geomIdx)
            self.hatList.append(texIdx)
            self.hatList.append(colorIdx)
        elif accessoryType == ToonDNA.GLASSES:
            self.glassesList.append(geomIdx)
            self.glassesList.append(texIdx)
            self.glassesList.append(colorIdx)
        elif accessoryType == ToonDNA.BACKPACK:
            self.backpackList.append(geomIdx)
            self.backpackList.append(texIdx)
            self.backpackList.append(colorIdx)
        elif accessoryType == ToonDNA.SHOES:
            self.shoesList.append(geomIdx)
            self.shoesList.append(texIdx)
            self.shoesList.append(colorIdx)
        return 1

    def replaceItemInAccessoriesList(self, accessoryType, geomIdxA, texIdxA, colorIdxA, geomIdxB, texIdxB, colorIdxB):
        if accessoryType == ToonDNA.HAT:
            itemList = self.hatList
        elif accessoryType == ToonDNA.GLASSES:
            itemList = self.glassesList
        elif accessoryType == ToonDNA.BACKPACK:
            itemList = self.backpackList
        elif accessoryType == ToonDNA.SHOES:
            itemList = self.shoesList
        else:
            return 0
        index = 0
        for i in range(0, len(itemList), 3):
            if itemList[i] == geomIdxA and itemList[i + 1] == texIdxA and itemList[i + 2] == colorIdxA:
                if accessoryType == ToonDNA.HAT:
                    self.hatList[i] = geomIdxB
                    self.hatList[i + 1] = texIdxB
                    self.hatList[i + 2] = colorIdxB
                elif accessoryType == ToonDNA.GLASSES:
                    self.glassesList[i] = geomIdxB
                    self.glassesList[i + 1] = texIdxB
                    self.glassesList[i + 2] = colorIdxB
                elif accessoryType == ToonDNA.BACKPACK:
                    self.backpackList[i] = geomIdxB
                    self.backpackList[i + 1] = texIdxB
                    self.backpackList[i + 2] = colorIdxB
                else:
                    self.shoesList[i] = geomIdxB
                    self.shoesList[i + 1] = texIdxB
                    self.shoesList[i + 2] = colorIdxB
                return 1

        return 0

    def removeItemInAccessoriesList(self, accessoryType, geomIdx, texIdx, colorIdx):
        if accessoryType == ToonDNA.HAT:
            itemList = self.hatList
        elif accessoryType == ToonDNA.GLASSES:
            itemList = self.glassesList
        elif accessoryType == ToonDNA.BACKPACK:
            itemList = self.backpackList
        elif accessoryType == ToonDNA.SHOES:
            itemList = self.shoesList
        else:
            return 0
        listLen = len(itemList)
        if listLen < 3:
            print('Accessory list is not long enough to delete anything')
            return 0
        index = 0
        for i in range(0, len(itemList), 3):
            if itemList[i] == geomIdx and itemList[i + 1] == texIdx and itemList[i + 2] == colorIdx:
                itemList = itemList[0:i] + itemList[i + 3:listLen]
                if accessoryType == ToonDNA.HAT:
                    self.hatList = itemList[:]
                    styles = ToonDNA.HatStyles
                    descDict = TTLocalizer.HatStylesDescriptions
                elif accessoryType == ToonDNA.GLASSES:
                    self.glassesList = itemList[:]
                    styles = ToonDNA.GlassesStyles
                    descDict = TTLocalizer.GlassesStylesDescriptions
                elif accessoryType == ToonDNA.BACKPACK:
                    self.backpackList = itemList[:]
                    styles = ToonDNA.BackpackStyles
                    descDict = TTLocalizer.BackpackStylesDescriptions
                elif accessoryType == ToonDNA.SHOES:
                    self.shoesList = itemList[:]
                    styles = ToonDNA.ShoesStyles
                    descDict = TTLocalizer.ShoesStylesDescriptions
                styleName = 'none'
                for style in styles.items():
                    if style[1] == [geomIdx, texIdx, colorIdx]:
                        styleName = style[0]
                        break

                return 1

        return 0

    def getMaxAccessories(self):
        return self.maxAccessories

    def isTrunkFull(self, extraAccessories = 0):
        numAccessories = (len(self.hatList) + len(self.glassesList) + len(self.backpackList) + len(self.shoesList)) / 3
        return numAccessories + extraAccessories >= self.maxAccessories

    def d_setHatList(self, hatList):
        self.sendUpdate('setHatList', [hatList])

    def setHatList(self, hatList):
        self.hatList = hatList

    def b_setHatList(self, hatList):
        self.setHatList(hatList)
        self.d_setHatList(hatList)

    def getHatList(self):
        return self.hatList

    def d_setGlassesList(self, glassesList):
        self.sendUpdate('setGlassesList', [glassesList])

    def setGlassesList(self, glassesList):
        self.glassesList = glassesList

    def b_setGlassesList(self, glassesList):
        self.setGlassesList(glassesList)
        self.d_setGlassesList(glassesList)

    def getGlassesList(self):
        return self.glassesList

    def d_setBackpackList(self, backpackList):
        self.sendUpdate('setBackpackList', [backpackList])

    def setBackpackList(self, backpackList):
        self.backpackList = backpackList

    def b_setBackpackList(self, backpackList):
        self.setBackpackList(backpackList)
        self.d_setBackpackList(backpackList)

    def getBackpackList(self):
        return self.backpackList

    def d_setShoesList(self, shoesList):
        self.sendUpdate('setShoesList', [shoesList])

    def setShoesList(self, shoesList):
        self.shoesList = shoesList

    def b_setShoesList(self, shoesList):
        self.setShoesList(shoesList)
        self.d_setShoesList(shoesList)

    def getShoesList(self):
        return self.shoesList

    def b_setHat(self, hatId, tex, color):
        self.setHat(hatId, tex, color)
        self.d_setHat(hatId, tex, color)

    def setHat(self, hatId, tex, color):
        self.hat = (hatId, tex, color)

    def d_setHat(self, hatId, tex, color):
        self.sendUpdate('setHat', [hatId, tex, color])

    def getHat(self):
        return self.hat

    def b_setGlasses(self, glassesId, tex, color):
        self.setGlasses(glassesId, tex, color)
        self.d_setGlasses(glassesId, tex, color)

    def setGlasses(self, glassesId, tex, color):
        self.glasses = (glassesId, tex, color)

    def d_setGlasses(self, shoesId, tex, color):
        self.sendUpdate('setGlasses', [shoesId, tex, color])

    def getGlasses(self):
        return self.glasses

    def b_setBackpack(self, backpackId, tex, color):
        self.setBackpack(backpackId, tex, color)
        self.d_setBackpack(backpackId, tex, color)

    def setBackpack(self, backpackId, tex, color):
        self.backpack = (backpackId, tex, color)

    def d_setBackpack(self, backpackId, tex, color):
        self.sendUpdate('setBackpack', [backpackId, tex, color])

    def getBackpack(self):
        return self.backpack

    def b_setShoes(self, shoesId, tex, color):
        self.setShoes(shoesId, tex, color)
        self.d_setShoes(shoesId, tex, color)

    def setShoes(self, shoesId, tex, color):
        self.shoes = (shoesId, tex, color)

    def d_setShoes(self, shoesId, tex, color):
        self.sendUpdate('setShoes', [shoesId, tex, color])

    def getShoes(self):
        return self.shoes

    def getGardenSpecials(self):
        return []

    def b_setEmoteAccess(self, bits):
        self.setEmoteAccess(bits)
        self.d_setEmoteAccess(bits)

    def d_setEmoteAccess(self, bits):
        self.sendUpdate('setEmoteAccess', [bits])

    def setEmoteAccess(self, bits):
        self.emoteAccess = bits

    def getEmoteAccess(self):
        return self.emoteAccess

    def b_setCustomMessages(self, customMessages):
        self.d_setCustomMessages(customMessages)
        self.setCustomMessages(customMessages)

    def d_setCustomMessages(self, customMessages):
        self.sendUpdate('setCustomMessages', [customMessages])

    def setCustomMessages(self, customMessages):
        self.customMessages = customMessages

    def getCustomMessages(self):
        return self.customMessages

    def getResistanceMessages(self):
        return []

    def getPetTrickPhrases(self):
        return self.petTrickPhrases

    def b_setCatalogSchedule(self, currentWeek, nextTime):
        self.setCatalogSchedule(currentWeek, nextTime)
        self.d_setCatalogSchedule(currentWeek, nextTime)

    def d_setCatalogSchedule(self, currentWeek, nextTime):
        self.sendUpdate('setCatalogSchedule', [currentWeek, nextTime])

    def setCatalogSchedule(self, currentWeek, nextTime):
        self.catalogScheduleCurrentWeek = currentWeek
        self.catalogScheduleNextTime = nextTime

        if self.air.doLiveUpdates:
            taskName = self.uniqueName('next-catalog')
            taskMgr.remove(taskName)
            duration = max(10.0, nextTime * 60 - time.time())
            taskMgr.doMethodLater(duration, self.__deliverCatalog, taskName)

    def getCatalogSchedule(self):
        return (self.catalogScheduleCurrentWeek, self.catalogScheduleNextTime)

    def __deliverCatalog(self, task):
        self.air.catalogManager.deliverCatalogFor(self)

        if task:
            return task.done

    def getCatalog(self):
        return (self.monthlyCatalog.getBlob(), self.weeklyCatalog.getBlob(), self.backCatalog.getBlob())

    def setBothSchedules(self, onOrder, onGiftOrder, doUpdateLater = True):
        if onOrder is not None:
            self.onOrder = CatalogItemList(onOrder, store = CatalogItem.Customization | CatalogItem.DeliveryDate)
        if onGiftOrder is not None:
            self.onGiftOrder = CatalogItemList(onGiftOrder, store = CatalogItem.Customization | CatalogItem.DeliveryDate)
        if not hasattr(self, 'air') or self.air is None:
            return
        if doUpdateLater and self.air.doLiveUpdates and hasattr(self, 'name'):
            taskName = f'next-bothDelivery-{self.do_id}'
            now = int(time.time() / 60 + 0.5)
            nextItem = None
            nextGiftItem = None
            nextTime = 0
            nextGiftTime = 0
            if self.onOrder:
                nextTime = self.onOrder.getNextDeliveryDate()
                nextItem = self.onOrder.getNextDeliveryItem()
            if self.onGiftOrder:
                nextGiftTime = self.onGiftOrder.getNextDeliveryDate()
                nextGiftItem = self.onGiftOrder.getNextDeliveryItem()
            if not nextTime:
                nextTime = nextGiftTime
            if not nextGiftTime:
                nextGiftTime = nextTime
            if nextGiftTime < nextTime:
                nextTime = nextGiftTime
            existingDuration = 0
            checkTaskList = taskMgr.getTasksNamed(taskName)
            if checkTaskList:
                currentTime = globalClock.getFrameTime()
                checkTask = checkTaskList[0]
                existingDuration = checkTask.wakeTime - currentTime
            if nextTime:
                newDuration = max(10.0, nextTime * 60 - time.time())
                if existingDuration and existingDuration >= newDuration:
                    taskMgr.remove(taskName)
                    taskMgr.doMethodLater(newDuration, self.__deliverBothPurchases, taskName)
                elif existingDuration and existingDuration < newDuration:
                    pass
                else:
                    taskMgr.doMethodLater(newDuration, self.__deliverBothPurchases, taskName)

    def __deliverBothPurchases(self, task):
        now = int(time.time() / 60 + 0.5)
        delivered, remaining = self.onOrder.extractDeliveryItems(now)
        deliveredGifts, remainingGifts = self.onGiftOrder.extractDeliveryItems(now)
        simbase.air.deliveryManager.sendDeliverGifts(self.do_id, now)
        giftItem = CatalogItemList(deliveredGifts, store = CatalogItem.Customization | CatalogItem.DeliveryDate)
        self.b_setMailboxContents(self.mailboxContents + delivered + deliveredGifts)
        self.b_setCatalogNotify(self.catalogNotify, ToontownGlobals.NewItems)
        self.b_setBothSchedules(remaining, remainingGifts)
        return Task.done

    def b_setMailboxContents(self, mailboxContents):
        self.setMailboxContents(mailboxContents)
        self.d_setMailboxContents(mailboxContents)

    def d_setMailboxContents(self, mailboxContents):
        self.sendUpdate('setMailboxContents', [mailboxContents.getBlob(store = CatalogItem.Customization)])

        if len(mailboxContents) == 0:
            self.b_setCatalogNotify(self.catalogNotify, ToontownGlobals.NoItems)

        self.checkMailboxFullIndicator()

    def checkMailboxFullIndicator(self):
        if self.houseId and hasattr(self, 'air'):
            if self.air:
                house = self.air.doTable.get(self.houseId)

                if house and house.mailbox:
                    house.mailbox.b_setFullIndicator(len(self.mailboxContents) != 0 or self.numMailItems or self.getNumInvitesToShowInMailbox() or len(self.awardMailboxContents) != 0)

    def setMailboxContents(self, mailboxContents):
        self.mailboxContents = CatalogItemList(mailboxContents, store = CatalogItem.Customization)

    def getMailboxContents(self):
        return self.mailboxContents.getBlob(store = CatalogItem.Customization)

    def getDeliverySchedule(self):
        return self.onOrder.getBlob(store = CatalogItem.Customization | CatalogItem.DeliveryDate)

    def b_setBothSchedules(self, onOrder, onGiftOrder, doUpdateLater = True):
        self.setBothSchedules(onOrder, onGiftOrder, doUpdateLater)
        self.d_setDeliverySchedule(onOrder)

    def getGiftSchedule(self):
        return self.onGiftOrder.getBlob(store = CatalogItem.Customization | CatalogItem.DeliveryDate)

    def b_setAwardMailboxContents(self, awardMailboxContents):
        self.setAwardMailboxContents(awardMailboxContents)
        self.d_setAwardMailboxContents(awardMailboxContents)

    def d_setAwardMailboxContents(self, awardMailboxContents):
        self.sendUpdate('setAwardMailboxContents', [awardMailboxContents.getBlob(store=CatalogItem.Customization)])

    def setAwardMailboxContents(self, awardMailboxContents):
        self.awardMailboxContents = CatalogItemList(awardMailboxContents, store = CatalogItem.Customization)

        if len(awardMailboxContents) == 0:
            self.b_setAwardNotify(ToontownGlobals.NoItems)

        self.checkMailboxFullIndicator()

    def getAwardMailboxContents(self):
        return self.awardMailboxContents.getBlob(store = CatalogItem.Customization)

    def getAwardSchedule(self):
        return b''

    def b_setAwardNotify(self, awardMailboxNotify):
        self.setAwardNotify(awardMailboxNotify)
        self.d_setAwardNotify(awardMailboxNotify)

    def d_setAwardNotify(self, awardMailboxNotify):
        self.sendUpdate('setAwardNotify', [awardMailboxNotify])

    def setAwardNotify(self, awardNotify):
        self.awardNotify = awardNotify

    def getAwardNotify(self):
        return self.awardNotify

    def b_setCatalogNotify(self, catalogNotify, mailboxNotify):
        self.setCatalogNotify(catalogNotify, mailboxNotify)
        self.d_setCatalogNotify(catalogNotify, mailboxNotify)

    def d_setCatalogNotify(self, catalogNotify, mailboxNotify):
        self.sendUpdate('setCatalogNotify', [catalogNotify, mailboxNotify])

    def setCatalogNotify(self, catalogNotify, mailboxNotify):
        self.catalogNotify = catalogNotify
        self.mailboxNotify = mailboxNotify

    def b_setCatalog(self, monthlyCatalog, weeklyCatalog, backCatalog):
        self.setCatalog(monthlyCatalog, weeklyCatalog, backCatalog)
        self.d_setCatalog(monthlyCatalog, weeklyCatalog, backCatalog)

    def d_setCatalog(self, monthlyCatalog, weeklyCatalog, backCatalog):
        self.sendUpdate('setCatalog', [monthlyCatalog.getBlob(), weeklyCatalog.getBlob(), backCatalog.getBlob()])

    def setCatalog(self, monthlyCatalog, weeklyCatalog, backCatalog):
        self.monthlyCatalog = CatalogItemList(monthlyCatalog)
        self.weeklyCatalog = CatalogItemList(weeklyCatalog)
        self.backCatalog = CatalogItemList(backCatalog)

    def getCatalogNotify(self):
        return (self.catalogNotify, self.mailboxNotify)

    def b_setDeliverySchedule(self, onOrder, doUpdateLater = True):
        self.setDeliverySchedule(onOrder, doUpdateLater)
        self.d_setDeliverySchedule(onOrder)

    def d_setDeliverySchedule(self, onOrder):
        self.sendUpdate('setDeliverySchedule', [onOrder.getBlob(store = CatalogItem.Customization | CatalogItem.DeliveryDate)])

    def setDeliverySchedule(self, onOrder, doUpdateLater = True):
        self.setBothSchedules(onOrder, None)

    def getSpeedChatStyleIndex(self):
        return 1

    def getTeleportAccess(self):
        return []

    def getCogStatus(self):
        return [0] * 32

    def getCogCount(self):
        return [0] * 32

    def getCogRadar(self):
        return [0] * 4

    def getBuildingRadar(self):
        return [0] * 4

    def getCogLevels(self):
        return [0] * 4

    def getCogTypes(self):
        return [0] * 4

    def getCogParts(self):
        return [0] * 4

    def getCogMerits(self):
        return [0] * 4

    def setHouseId(self, houseId):
        self.houseId = houseId

    def getHouseId(self):
        return self.houseId

    def b_setQuests(self, questList):
        flattenedQuests = []

        for quest in questList:
            flattenedQuests.extend(quest)

        self.setQuests(flattenedQuests)
        self.d_setQuests(flattenedQuests)

    def d_setQuests(self, flattenedQuests):
        self.sendUpdate('setQuests', [flattenedQuests])

    def setQuests(self, flattenedQuests):
        questList = []
        questLen = 5

        for i in range(0, len(flattenedQuests), questLen):
            questList.append(flattenedQuests[i:i + questLen])

        self.quests = questList

    def getQuests(self):
        flattenedQuests = []
        for quest in self.quests:
            flattenedQuests.extend(quest)

        return flattenedQuests

    def getQuestHistory(self):
        return []

    def getRewardHistory(self):
        return 0, []

    def getQuestCarryLimit(self):
        return 1

    def getCheesyEffect(self):
        return 0, 0, 0

    def getPosIndex(self):
        return 0

    def b_setFishCollection(self, genusList, speciesList, weightList):
        self.setFishCollection(genusList, speciesList, weightList)
        self.d_setFishCollection(genusList, speciesList, weightList)

    def d_setFishCollection(self, genusList, speciesList, weightList):
        self.sendUpdate('setFishCollection', [genusList, speciesList, weightList])

    def setFishCollection(self, genusList, speciesList, weightList):
        self.fishCollection = FishCollection()
        self.fishCollection.makeFromNetLists(genusList, speciesList, weightList)

    def getFishCollection(self):
        return self.fishCollection.getNetLists()

    def getMaxFishTank(self):
        return 20

    def setInventory(self, inventory):
        self.inventory = Inventory.fromBytes(inventory)
        self.inventory.toon = self

    def getInventory(self):
        return self.inventory.makeNetString()

    def b_setFishTank(self, genusList, speciesList, weightList):
        self.setFishTank(genusList, speciesList, weightList)
        self.d_setFishTank(genusList, speciesList, weightList)

    def d_setFishTank(self, genusList, speciesList, weightList):
        self.sendUpdate('setFishTank', [genusList, speciesList, weightList])

    def setFishTank(self, genusList, speciesList, weightList):
        self.fishTank = FishTank()
        self.fishTank.makeFromNetLists(genusList, speciesList, weightList)

    def getFishTank(self):
        return self.fishTank.getNetLists()

    def addFishToTank(self, fish):
        numFish = len(self.fishTank)
        if numFish >= self.getMaxFishTank():
            return 0
        if self.fishTank.addFish(fish):
            self.d_setFishTank(*self.getFishTank())
            return 1
        return 0

    def getFishingRod(self):
        return 0

    def b_setFishingTrophies(self, trophyList):
        self.setFishingTrophies(trophyList)
        self.d_setFishingTrophies(trophyList)

    def setFishingTrophies(self, trophyList):
        self.fishingTrophies = trophyList

    def d_setFishingTrophies(self, trophyList):
        self.sendUpdate('setFishingTrophies', [trophyList])

    def getFishingTrophies(self):
        return self.fishingTrophies

    def getFlowerCollection(self):
        return [], []

    def getFlowerBasket(self):
        return [], []

    def getMaxFlowerBasket(self):
        return 20

    def getGardenTrophies(self):
        return []

    def getShovel(self):
        return 0

    def getShovelSkill(self):
        return 0

    def getWateringCan(self):
        return 0

    def getWateringCanSkill(self):
        return 0

    def getPetId(self):
        return 0

    def getPetTutorialDone(self):
        return 0

    def getFishBingoTutorialDone(self):
        return 0

    def getFishBingoMarkTutorialDone(self):
        return 0

    def getKartBodyType(self):
        return -1

    def getKartBodyColor(self):
        return -1

    def getKartAccessoryColor(self):
        return -1

    def getKartEngineBlockType(self):
        return -1

    def getKartSpoilerType(self):
        return -1

    def getKartFrontWheelWellType(self):
        return -1

    def getKartBackWheelWellType(self):
        return -1

    def getKartRimType(self):
        return -1

    def getKartDecalType(self):
        return -1

    def getTickets(self):
        return 200

    def getKartingHistory(self):
        return [0] * 16

    def getKartingTrophies(self):
        return [0] * 33

    def getKartingPersonalBest(self):
        return [0] * 6

    def getKartingPersonalBest2(self):
        return [0] * 12

    def getKartAccessoriesOwned(self):
        return [0] * 16

    def getCogSummonsEarned(self):
        return [0] * 32

    def getGardenStarted(self):
        return 0

    def getGolfHistory(self):
        return [0] * 18

    def getPackedGolfHoleBest(self):
        return [0] * 18

    def getGolfCourseBest(self):
        return [0] * 3

    def setPinkSlips(self, pinkSlips):
        self.pinkSlips = pinkSlips

    def getPinkSlips(self):
        return self.pinkSlips

    def d_setPinkSlips(self, pinkSlips):
        self.sendUpdate('setPinkSlips', [pinkSlips])

    def b_setNametagStyle(self, nametagStyle):
        self.d_setNametagStyle(nametagStyle)
        self.setNametagStyle(nametagStyle)

    def d_setNametagStyle(self, nametagStyle):
        self.sendUpdate('setNametagStyle', [nametagStyle])

    def setNametagStyle(self, nametagStyle):
        self.nametagStyle = nametagStyle

    def getNametagStyle(self):
        return self.nametagStyle

    def b_setGhostMode(self, flag):
        self.setGhostMode(flag)
        self.d_setGhostMode(flag)

    def d_setGhostMode(self, flag):
        self.sendUpdate('setGhostMode', [flag])

    def setGhostMode(self, flag):
        self.ghostMode = flag

    def setNumMailItems(self, numMailItems):
        self.numMailItems = numMailItems

    def getNumInvitesToShowInMailbox(self):
        # Didn't feel like fixing up Disney logic for this at the moment.
        return 0

    def d_catalogGenClothes(self):
        self.sendUpdate('catalogGenClothes', [self.do_id])

    def d_catalogGenAccessories(self):
        self.sendUpdate('catalogGenAccessories', [self.do_id])

    def getHoodId(self, zoneId):
        return zoneId - zoneId % 1000

    def handleZoneChange(self, oldZone: int, newZone: int):
        channel = getPuppetChannel(self.do_id)

        if oldZone in self.air.vismap and newZone not in self.air.vismap:
            self.air.removeInterest(channel, DistributedToonAI.STREET_INTEREST_HANDLE, 0)
        elif newZone in self.air.vismap:
            visibles = self.air.vismap[newZone][:]
            if len(visibles) == 1 and visibles[0] == newZone:
                # Playground visgroup, ignore
                return
            self.air.setInterest(channel, DistributedToonAI.STREET_INTEREST_HANDLE, 0, self.parentId, visibles)

        # TODO: Should this be handled somewhere else?
        if 100 <= newZone < HoodGlobals.DynamicZonesBegin:
            hood = self.getHoodId(newZone)

            self.b_setLastHood(hood)
            self.b_setDefaultZone(hood)

            hoodsVisited = list(self.getHoodsVisited())

            if hood not in hoodsVisited:
                hoodsVisited.append(hood)
                self.b_setHoodsVisited(hoodsVisited)

from ai import OTPGlobals

class FishCollection:
    __slots__ = 'fishList'

    def __init__(self):
        self.fishList: List[FishBase] = []

    def __len__(self):
        return len(self.fishList)

    def getFish(self):
        return self.fishList

    def makeFromNetLists(self, genusList, speciesList, weightList):
        self.fishList: List[FishBase] = []
        for genus, species, weight in zip(genusList, speciesList, weightList):
            self.fishList.append(FishBase(genus, species, weight))

    def getNetLists(self):
        # This function Return lists formated for toon.dc style setting and getting.
        # We store parallel lists of genus, species, and weight in the database.
        genusList = []
        speciesList = []
        weightList = []
        for fish in self.fishList:
            genusList.append(fish.getGenus())
            speciesList.append(fish.getSpecies())
            weightList.append(fish.getWeight())
        return [genusList, speciesList, weightList]

    def hasFish(self, genus, species):
        for fish in self.fishList:
            if (fish.getGenus() == genus) and (fish.getSpecies() == species):
                return 1
        return 0

    def hasGenus(self, genus):
        for fish in self.fishList:
            if (fish.getGenus() == genus):
                return 1
        return 0

    def __collect(self, newFish, updateCollection):
        for fish in self.fishList:
            if ((fish.getGenus() == newFish.getGenus()) and
                (fish.getSpecies() == newFish.getSpecies())):
                if (fish.getWeight() < newFish.getWeight()):
                    if updateCollection:
                        fish.setWeight(newFish.getWeight())
                    return COLLECT_NEW_RECORD
                else:
                    return COLLECT_NO_UPDATE
        if updateCollection:
            self.fishList.append(newFish)
        return COLLECT_NEW_ENTRY

    def collectFish(self, newFish):
        return self.__collect(newFish, updateCollection=1)

    def getCollectResult(self, newFish):
        return self.__collect(newFish, updateCollection=0)

    def __str__(self):
        numFish = len(self.fishList)
        txt = f'Fish Collection ({numFish} fish):'
        for fish in self.fishList:
            txt += ('\n' + str(fish))
        return txt

class FishTank:
    __slots__ = 'fishList'

    def __init__(self):
        self.fishList: List[FishBase] = []

    def __len__(self):
        return len(self.fishList)

    def getFish(self):
        return self.fishList

    def makeFromNetLists(self, genusList, speciesList, weightList):
        self.fishList: List[FishBase] = []
        for genus, species, weight in zip(genusList, speciesList, weightList):
            self.fishList.append(FishBase(genus, species, weight))

    def getNetLists(self):
        genusList = []
        speciesList = []
        weightList = []
        for fish in self.fishList:
            genusList.append(fish.getGenus())
            speciesList.append(fish.getSpecies())
            weightList.append(fish.getWeight())
        return [genusList, speciesList, weightList]

    def hasFish(self, genus, species, weight):
        for fish in self.fishList:
            if (fish.getGenus() == genus) and (fish.getSpecies() == species):
                if fish.getWeight() >= weight:
                    return (1, 1)
                return (1, 0)
        return (0, 0)

    def addFish(self, fish):
        self.fishList.append(fish)
        return 1

    def removeFishAtIndex(self, index):
        if index >= len(self.fishList):
            return 0
        else:
            del self.fishList[i]
            return 1

    def getTotalValue(self):
        value = 0
        for fish in self.fishList:
            value += simbase.air.fishManager.getFishValue(fish.getGenus(), fish.getSpecies(), fish.getWeight())
        return value

    def __str__(self):
        numFish = len(self.fishList)
        value = 0
        txt = f'Fish Tank ({numFish} fish)'
        for fish in self.fishList:
            txt += ('\n' + str(fish))
            value += simbase.air.fishManager.getFishValue(fish.getGenus(), fish.getSpecies(), fish.getWeight())
        txt += f'\nTotal value: {value}'
        return txt

class Experience:
    __slots__ = 'experience', 'toon'

    def __init__(self, experience=None, toon=None):
        if not experience:
            self.experience = [0] * NUM_TRACKS
        else:
            self.experience = experience

        self.toon = toon

    def __getitem__(self, key):
        if not type(key) == int and not type(key) == Tracks:
            raise IndexError

        return self.experience[key]

    @staticmethod
    def fromBytes(data):
        dg = Datagram(data)
        return Experience.fromNetString(DatagramIterator(dg))

    @staticmethod
    def fromNetString(dgi):
        return Experience([dgi.getUint16() for _ in range(NUM_TRACKS)])

    def makeNetString(self):
        return b''.join((trackExp.to_bytes(2, 'little') for trackExp in self.experience))

    def addExp(self, track, amount=1):
        current = self.experience[track]

        if self.toon.getAccess() == OTPGlobals.AccessFull:
            maxExp = MaxSkill
        else:
            maxExp = getGagTrack(track).unpaidMaxSkill

        self.experience[track] = min(current + amount, maxExp)

    def getExpLevel(self, track: int) -> int:
        xp = self[track]
        xpLevels = getGagTrack(track).levels
        for amount in xpLevels:
            if xp < amount:
                return max(xpLevels.index(amount) - 1, 0)
        else:
            return len(xpLevels) - 1