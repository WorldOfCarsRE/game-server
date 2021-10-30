from ai.DistributedNodeAI import DistributedNodeAI
from ai.toon import NPCToons
from ai.toon.Inventory import Inventory
from ai.toon.ToonDNA import ToonDNA
from direct.task.Task import Task

SHIRT = 0x1
SHORTS = 0x2

TAILOR_COUNTDOWN_TIME = 300

class DistributedNPCToonBaseAI(DistributedNodeAI):
    def __init__(self, air, npcId, name = None):
        DistributedNodeAI.__init__(self, air, name)

        self.npcId = npcId
        self.hq = False
        self.name = name
        self.dna = ''
        self.index = 0
        self.occupier = 0

    def d_setMovie(self, movie, args = []):
        self.sendUpdate('setMovie', [movie, self.npcId, self.occupier, args, globalClockDelta.getRealNetworkTime()])

    def isOccupied(self):
        return self.occupier != 0

    def getName(self):
        return self.name

    def getDNAString(self):
        return self.dna

    def getPositionIndex(self):
        return self.index

    def d_setAnimState(self, animName, playRate):
        timestamp = globalClockDelta.getRealNetworkTime()
        self.sendUpdate('setAnimState', [animName, playRate, timestamp])

    def setPageNumber(self, paragraph, pageNumber, timestamp):
        pass

    def avatarEnter(self):
        sender = self.air.currentAvatarSender
        self.freeAvatar(sender)

    def freeAvatar(self, avId):
        self.sendUpdateToAvatar(avId, 'freeAvatar', [])

    def getGivesQuests(self):
        return True

class DistributedNPCToonAI(DistributedNPCToonBaseAI):
    def setMovieDone(self):
        pass

    def chooseQuest(self, choice):
        pass

    def chooseTrack(self, choice):
        pass

class DistributedNPCSpecialQuestGiverAI(DistributedNPCToonBaseAI):
    def setMovieDone(self):
        pass

    def chooseQuest(self, choice):
        pass

    def chooseTrack(self, choice):
        pass

class DistributedNPCClerkAI(DistributedNPCToonBaseAI):
    def getGivesQuests(self):
        return False

    def d_setMovie(self, movie):
        self.sendUpdate('setMovie', [movie, self.npcId, self.occupier, globalClockDelta.getRealNetworkTime()])

    def sendClearMovie(self):
        self.ignore(self.air.getDeleteDoIdEvent(self.occupier))
        self.occupier = 0
        self.timedOut = 0
        self.d_setMovie(NPCToons.PURCHASE_MOVIE_CLEAR)

    def sendTimeoutMovie(self, task):
        self.d_setMovie(NPCToons.SELL_MOVIE_TIMEOUT)
        self.sendClearMovie()

    def avatarEnter(self):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)

        if av is None:
            return

        if self.isOccupied():
            self.freeAvatar(avId)

        elif (av.getMoney()):
            self.occupier = avId
            self.acceptOnce(self.air.getDeleteDoIdEvent(avId), self.__handleUnexpectedExit, extraArgs = [avId])
            self.d_setMovie(NPCToons.PURCHASE_MOVIE_START)
            self.timedOut = 0
            taskMgr.doMethodLater(NPCToons.CLERK_COUNTDOWN_TIME, self.sendTimeoutMovie, self.uniqueName('clearMovie'))
        else:
            self.occupier = avId
            self.d_setMovie(NPCToons.PURCHASE_MOVIE_NO_MONEY)
            self.sendClearMovie()

    def __handleUnexpectedExit(self, avId):
        taskMgr.remove(self.uniqueName('clearMovie'))
        self.sendClearMovie()

    def setInventory(self, blob, newMoney, done):
        avId = self.air.currentAvatarSender

        av = self.air.doTable.get(avId)
        if not av:
            return

        if avId != self.occupier:
            return

        newInventory = Inventory.fromBytes(blob)
        newInventory.toon = av
        currentMoney = av.getMoney()

        if not av.inventory.validatePurchase(newInventory, currentMoney, newMoney):
            # Invalid purchase. Send updates to revert the changes on their end.
            print('INVALID PURCHASE', blob, newMoney)
            av.d_setInventory(av.inventory.makeNetString())
            av.d_setMoney(currentMoney)
            return

        av.inventory = newInventory
        av.money = newMoney

        if not done:
            return

        av.d_setInventory(av.inventory.makeNetString())
        av.d_setMoney(newMoney)

        self.d_setMovie(NPCToons.PURCHASE_MOVIE_COMPLETE)
        taskMgr.remove(self.uniqueName('clearMovie'))
        self.sendClearMovie()

class DistributedNPCTailorAI(DistributedNPCToonBaseAI):
    freeClothes = True
    housingEnabled = True

    def __init__(self, air, npcId, name):
        DistributedNPCToonBaseAI.__init__(self, air, npcId, name)

        self.timedOut = 0

        self.customerDNA = None
        self.customerId = None

    def getGivesQuests(self):
        return False

    def avatarEnter(self):
        avId = self.air.currentAvatarSender

        if not avId in self.air.doTable:
            return

        if self.isOccupied():
            self.freeAvatar(avId)
            return

        av = self.air.doTable[avId]

        self.customerDNA = ToonDNA()
        self.customerDNA.makeFromNetString(av.getDNAString())

        self.customerId = avId

        av.b_setDNAString(self.customerDNA.makeNetString())

        self.acceptOnce(self.air.getDeleteDoIdEvent(avId), self.handleUnexpectedExit, extraArgs = [avId])

        flag = NPCToons.PURCHASE_MOVIE_START_BROWSE

        if self.freeClothes:
            flag = NPCToons.PURCHASE_MOVIE_START

            if self.housingEnabled and self.isClosetAlmostFull(av):
                flag = NPCToons.PURCHASE_MOVIE_START_NOROOM

        elif self.air.questManager.hasTailorClothingTicket(av, self) == 1:
            flag = NPCToons.PURCHASE_MOVIE_START

            if self.housingEnabled and self.isClosetAlmostFull(av):
                flag = NPCToons.PURCHASE_MOVIE_START_NOROOM

        elif self.air.questManager.hasTailorClothingTicket(av, self) == 2:
            flag = NPCToons.PURCHASE_MOVIE_START

            if self.housingEnabled and self.isClosetAlmostFull(av):
                flag = NPCToons.PURCHASE_MOVIE_START_NOROOM

        self.sendShoppingMovie(avId, flag)

    def isClosetAlmostFull(self, av):
        numClothes = len(av.clothesTopsList) / 4 + len(av.clothesBottomsList) / 2

        if numClothes >= av.maxClothes - 1:
            return 1

        return 0

    def sendShoppingMovie(self, avId, flag):
        self.occupier = avId
        self.sendUpdate('setMovie', [flag, self.npcId, avId, globalClockDelta.getRealNetworkTime()])
        taskMgr.doMethodLater(TAILOR_COUNTDOWN_TIME, self.sendTimeoutMovie, self.uniqueName('clearMovie'))

    def rejectAvatar(self, avId):
        pass

    def sendTimeoutMovie(self, task):
        toon = self.air.doTable.get(self.customerId)

        if toon != None and self.customerDNA:
            toon.b_setDNAString(self.customerDNA.makeNetString())

        self.timedOut = 1

        self.sendUpdate('setMovie', [NPCToons.PURCHASE_MOVIE_TIMEOUT, self.npcId, self.occupier, globalClockDelta.getRealNetworkTime()])

        self.sendClearMovie(None)

        return Task.done

    def sendClearMovie(self, task):
        self.ignore(self.air.getDeleteDoIdEvent(self.occupier))

        self.customerDNA = None
        self.customerId = None
        self.occupier = 0
        self.timedOut = 0

        self.sendUpdate('setMovie', [NPCToons.PURCHASE_MOVIE_CLEAR, self.npcId, 0, globalClockDelta.getRealNetworkTime()])
        self.sendUpdate('setCustomerDNA', [0, ''])

        return Task.done

    def completePurchase(self, avId):
        self.occupier = avId

        self.sendUpdate('setMovie', [NPCToons.PURCHASE_MOVIE_COMPLETE, self.npcId, avId, globalClockDelta.getRealNetworkTime()])

        self.sendClearMovie(None)

    def setDNA(self, dna, finished, which):
        avId = self.air.currentAvatarSender

        if avId != self.customerId:
            return

        # TODO: DNA validation.

        if avId in self.air.doTable:
            av = self.air.doTable[avId]

            if finished == 2 and which > 0:
                if self.air.questManager.removeClothingTicket(av, self) == 1 or self.freeClothes:
                    av.b_setDNAString(dna)

                    if which & SHIRT:
                        if av.addToClothesTopsList(self.customerDNA.topTex, self.customerDNA.topTexColor, self.customerDNA.sleeveTex, self.customerDNA.sleeveTexColor) == 1:
                            av.b_setClothesTopsList(av.getClothesTopsList())

                    if which & SHORTS:
                        if av.addToClothesBottomsList(self.customerDNA.botTex, self.customerDNA.botTexColor) == 1:
                            av.b_setClothesBottomsList(av.getClothesBottomsList())

                    if self.customerDNA:
                        av.b_setDNAString(self.customerDNA.makeNetString())

            elif finished == 1:
                if self.customerDNA:
                    av.b_setDNAString(self.customerDNA.makeNetString())
            else:
                self.sendUpdate('setCustomerDNA', [avId, dna])

        if self.timedOut == 1 or finished == 0:
            return

        if self.occupier == avId:
            taskMgr.remove(self.uniqueName('clearMovie'))
            self.completePurchase(avId)

    def handleUnexpectedExit(self, avId):
        if self.customerId == avId:
            toon = self.air.doTable.get(avId)

            if toon == None:
                # TODO
                return

            if self.customerDNA:
                toon.b_setDNAString(self.customerDNA.makeNetString())

                # TODO

        if self.occupier == avId:
            self.sendClearMovie(None)

class DistributedNPCFishermanAI(DistributedNPCToonBaseAI):
    def getGivesQuests(self):
        return False

    def sendClearMovie(self):
        self.ignore(self.air.getDeleteDoIdEvent(self.occupier))
        self.occupier = 0
        self.d_setMovie(NPCToons.PURCHASE_MOVIE_CLEAR)

    def sendTimeoutMovie(self, task):
        self.d_setMovie(NPCToons.SELL_MOVIE_TIMEOUT)
        self.sendClearMovie()

    def avatarEnter(self):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)

        if av is None:
            return

        if self.isOccupied():
            self.freeAvatar(avId)

        elif av.fishTank.getTotalValue():
            self.occupier = avId
            self.acceptOnce(self.air.getDeleteDoIdEvent(avId), self.__handleUnexpectedExit, extraArgs = [avId])
            self.d_setMovie(NPCToons.SELL_MOVIE_START)
            taskMgr.doMethodLater(NPCToons.CLERK_COUNTDOWN_TIME, self.sendTimeoutMovie, self.uniqueName('clearMovie'))
        else:
            self.occupier = avId
            self.d_setMovie(NPCToons.SELL_MOVIE_NOFISH)
            self.sendClearMovie()

    def __handleUnexpectedExit(self, avId):
        taskMgr.remove(self.uniqueName('clearMovie'))
        self.sendClearMovie()

    def completeSale(self, sell: bool):
        avId = self.air.currentAvatarSender

        if self.occupier != avId:
            # TODO: We need to write a event here.
            return

        av = self.air.doTable.get(avId)

        if not av:
            return

        if sell:
            trophyResult = self.air.fishManager.creditFishTank(av)

            if trophyResult:
                movieType = NPCToons.SELL_MOVIE_TROPHY
                extraArgs = [len(av.fishCollection), self.air.fishManager.totalFish]
            else:
                movieType = NPCToons.SELL_MOVIE_COMPLETE
                extraArgs = []

            self.d_setMovie(movieType, args = extraArgs)
        else:
            self.d_setMovie(NPCToons.SELL_MOVIE_NOFISH)

        taskMgr.remove(self.uniqueName('clearMovie'))
        self.sendClearMovie()

class DistributedNPCPartyPersonAI(DistributedNPCToonBaseAI):
    def avatarEnter(self):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)

        if av is None:
            return

        if self.isOccupied():
            self.freeAvatar(avId)

        # TODO
        flag = NPCToons.PARTY_MOVIE_COMINGSOON
        self.d_setMovie(avId, flag)
        self.sendClearMovie()

    def sendClearMovie(self):
        self.ignore(self.air.getDeleteDoIdEvent(self.occupier))
        self.occupier = 0
        self.d_setMovie(0, NPCToons.PARTY_MOVIE_CLEAR)

    def d_setMovie(self, avId, flag, extraArgs = []):
        self.sendUpdate('setMovie', [flag, self.npcId, avId, extraArgs, globalClockDelta.getRealNetworkTime()])

    def answer(self, plan: bool):
        pass

class DistributedNPCPetclerkAI(DistributedNPCToonBaseAI):
    def getGivesQuests(self):
        return False

    def petAdopted(self, whichPet, nameIndex):
        pass

    def petReturned(self):
        pass

    def fishSold(self):
        pass

    def transactionDone(self):
        pass

class DistributedNPCKartClerkAI(DistributedNPCToonBaseAI):
    def buyKart(self, kart):
        pass

    def buyAccessory(self, accessory):
        pass

    def transactionDone(self):
        pass

class DistributedNPCFlippyInToonHallAI(DistributedNPCToonAI):
    pass

class DistributedNPCScientistAI(DistributedNPCToonBaseAI):
    pass