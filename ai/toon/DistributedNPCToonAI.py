from ai.DistributedNodeAI import DistributedNodeAI
from ai.toon import NPCToons

class DistributedNPCToonBaseAI(DistributedNodeAI):
    def __init__(self, air, npcId, name=None):
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
    def setInventory(self, inventory, money, done):
        pass

class DistributedNPCTailorAI(DistributedNPCToonBaseAI):
    def setDNA(self, dna, finished, which):
        pass

class DistributedNPCFishermanAI(DistributedNPCToonBaseAI):
    def sendClearMovie(self, task = None):
        self.ignore(self.air.getAvatarExitEvent(self.occupier))
        self.occupier = 0
        self.d_setMovie(NPCToons.PURCHASE_MOVIE_CLEAR)

    def avatarEnter(self):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)

        if av is None:
            return

        if self.isOccupied():
            self.freeAvatar(avId)

        elif av.fishTank.getTotalValue():
            self.occupier = avId
            self.acceptOnce(self.air.getAvatarExitEvent(avId), self.__handleUnexpectedExit, extraArgs = [avId])
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
        pass

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
        self.ignore(self.air.getAvatarExitEvent(self.occupier))
        self.occupier = 0
        self.d_setMovie(0, NPCToons.PARTY_MOVIE_CLEAR)

    def d_setMovie(self, avId, flag, extraArgs = []):
        self.sendUpdate('setMovie', [flag, self.npcId, avId, extraArgs, globalClockDelta.getRealNetworkTime()])

    def answer(self, plan: bool):
        pass

class DistributedNPCPetclerkAI(DistributedNPCToonBaseAI):
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