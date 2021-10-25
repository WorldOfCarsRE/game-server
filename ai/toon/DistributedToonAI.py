from ai.DistributedObjectAI import DistributedObjectAI
from ai.DistributedSmoothNodeAI import DistributedSmoothNodeAI
from otp.util import getPuppetChannel
from dc.util import Datagram

from typing import NamedTuple, List, Dict
from ai.battle.BattleGlobals import *
from ai.globals import HoodGlobals
from ai.fishing.FishBase import FishBase
from ai.fishing.FishCollectionEnum import *
from ai.toon.Inventory import Inventory

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
        self.defaultZone = 0
        self.lastHood = 0
        self.hoodsVisited = []
        self.fishingTrophies = []

    def delete(self):
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

        self.dnaString = ''
        self.hp = 15
        self.maxHp = 15
        self.maxMoney = 40
        self.money = 0
        self.bankMoney = 0
        self.maxBankMoney = 1000
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

    def setDNAString(self, dnaString):
        self.dnaString = dnaString

    def getDNAString(self):
        return self.dnaString

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

    def getMaxClothes(self):
        return 0

    def getClothesTopsList(self):
        return []

    def getClothesBottomsList(self):
        return []

    def getMaxAccessories(self):
        return 0

    def getHatList(self):
        return []

    def getGlassesList(self):
        return []

    def getBackpackList(self):
        return []

    def getShoesList(self):
        return []

    def getHat(self):
        return 0, 0, 0

    def getGlasses(self):
        return 0, 0, 0

    def getBackpack(self):
        return 0, 0, 0

    def getShoes(self):
        return 0, 0, 0

    def getGardenSpecials(self):
        return []

    def getEmoteAccess(self):
        return [1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    def getCustomMessages(self):
        return []

    def getResistanceMessages(self):
        return []

    def getPetTrickPhrases(self):
        return []

    def getCatalogSchedule(self):
        return 0, 0

    def getCatalog(self):
        return b'', b'', b''

    def getMailboxContents(self):
        return b''

    def getDeliverySchedule(self):
        return b''

    def getGiftSchedule(self):
        return b''

    def getAwardMailboxContents(self):
        return b''

    def getAwardSchedule(self):
        return b''

    def getAwardNotify(self):
        return 0

    def getCatalogNotify(self):
        return 0, 0

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

    def getHouseId(self):
        return 0

    def getQuests(self):
        return []

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

    def getNametagStyle(self):
        return 0

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
        '''
        Return lists formated for toon.dc style setting and getting
        We store parallel lists of genus, species, and weight in the db
        '''
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
        return Experience.fromNetString(Datagram(data).iterator())

    @staticmethod
    def fromNetString(dgi):
        return Experience([dgi.get_uint16() for _ in range(NUM_TRACKS)])

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