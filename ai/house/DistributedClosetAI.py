from ai.house.DistributedFurnitureItemAI import DistributedFurnitureItemAI
from ai.toon.DistributedToonAI import DistributedToonAI
from ai.toon.ToonDNA import ToonDNA
from typing import List

SHIRT = 0x1
SHORTS = 0x2

CLOSET_MOVIE_COMPLETE = 1
CLOSET_MOVIE_CLEAR = 2
CLOSET_MOVIE_TIMEOUT = 3

CLOSED = 0
OPEN = 1

TIMEOUT_TIME = 200

class DistributedClosetAI(DistributedFurnitureItemAI):

    def __init__(self, air, furnitureMgr, item):
        DistributedFurnitureItemAI.__init__(self, air, furnitureMgr, item)
        self.ownerId = self.furnitureMgr.house.avId
        self.ownerAv = None
        self.timedOut = 0
        self.occupied = 0
        self.customerDNA = None
        self.customerId = None
        self.deletedTops: List[int] = []
        self.deletedBottoms: List[int] = []
        self.dummyToonAI = None
        self.busy = 0

    def delete(self):
        self.ignoreAll()
        self.customerDNA = None
        self.customerId = None
        del self.deletedTops
        del self.deletedBottoms

    def handleExitedAvatar(self, avId):
        self.sendClearMovie()

    def getOwnerId(self):
        return self.ownerId

    def d_freeAvatar(self, avId):
        self.sendUpdateToAvatar(avId, 'freeAvatar', [])

    def d_setMovie(self, mode):
        self.sendUpdate('setMovie', [mode, self.occupied, globalClockDelta.getRealNetworkTime()])

    def d_setCustomerDNA(self, avId, dnaString):
        self.sendUpdate('setCustomerDNA', [avId, dnaString])

    def sendClearMovie(self):
        self.ignoreAll()
        self.customerDNA = None
        self.customerId = None
        self.occupied = 0
        self.timedOut = 0

        self.d_setMovie(CLOSET_MOVIE_CLEAR)
        #self.d_setState()
        self.d_setCustomerDNA(0, '')

        if self.dummyToonAI:
            self.dummyToonAI.deleteDummy()
            self.dummyToonAI = None

        self.ownerAv = None

    def sendTimeoutMovie(self, task):
        av = self.air.doTable.get(self.customerId)

        if av != None and self.customerDNA:
            av.b.setDNAString(self.customerDNA.makeNetString())

        self.timedOut = 1
        self.d_setMovie(CLOSET_MOVIE_TIMEOUT)
        self.endClearMovie()

        return task.done

    def enterAvatar(self):
        avId = self.air.currentAvatarSender

        if self.busy > 0:
            self.freeAvatar(avId)
            return

        av = self.air.doTable.get(avId)

        if not av:
            return

        self.customerDNA = ToonDNA()
        self.customerDNA.makeFromNetString(av.getDNAString())

        self.customerId = avId
        self.busy = avId

        self.acceptOnce(self.air.getDeleteDoIdEvent(avId), self.handleUnexpectedExit, extraArgs = [avId])
        self.acceptOnce(f'bootAvFromEstate-{str(avId)}', self.handleBootMessage, extraArgs = [avId])

        if self.ownerId:
            self.ownerAv = None
            if self.ownerId in self.air.doTable:
                self.ownerAv = self.air.doTable[self.ownerId]
                self.__openCloset()
            else:
                # TODO
                pass
        else:
            self.completePurchase(avId)

    def __openCloset(self):
        topList = self.ownerAv.getClothesTopsList()
        botList = self.ownerAv.getClothesBottomsList()

        self.sendUpdate('setState', [OPEN, self.customerId, self.ownerAv.do_id, self.ownerAv.dna.gender, topList, botList])

        taskMgr.doMethodLater(TIMEOUT_TIME, self.sendTimeoutMovie, self.uniqueName('clearMovie'))

    def completePurchase(self, avId):
        self.busy = avId
        self.sendUpdate('setMovie', [CLOSET_MOVIE_COMPLETE, avId, globalClockDelta.getRealNetworkTime()])
        self.sendClearMovie()

    def removeItem(self, trashBlob, which):
        pass

    def setDNA(self, blob, finished, which):
        avId = self.air.currentAvatarSender

        if avId != self.customerId:
            return

        if avId in self.air.doTable:
            av = self.air.doTable[avId]

            # TODO: Check DNA for security.

            if (finished == 2):
                newDNA = self.updateToonClothes(av, blob)

                if which & ClosetGlobals.SHIRT:
                    if av.replaceItemInClothesTopsList(newDNA.topTex,
                                                       newDNA.topTexColor,
                                                       newDNA.sleeveTex,
                                                       newDNA.sleeveTexColor,
                                                       self.customerDNA.topTex,
                                                       self.customerDNA.topTexColor,
                                                       self.customerDNA.sleeveTex,
                                                       self.customerDNA.sleeveTexColor) == 1:
                        av.b_setClothesTopsList(av.getClothesTopsList())

                if which & ClosetGlobals.SHORTS:
                    if av.replaceItemInClothesBottomsList(newDNA.botTex,
                                                          newDNA.botTexColor,
                                                          self.customerDNA.botTex,
                                                          self.customerDNA.botTexColor) == 1:
                        av.b_setClothesBottomsList(av.getClothesBottomsList())

                self.__finalizeDelete(avId)

            elif (finished == 1):
                if self.customerDNA:
                    av.b_setDNAString(self.customerDNA.makeNetString())

                    self.deletedTops = []
                    self.deletedBottoms = []
            else:
                self.sendUpdate('setCustomerDNA', [avId, blob])

        if (self.timedOut == 1 or finished == 0 or finished == 4):
            return

        if (self.busy == avId):
            taskMgr.remove(self.uniqueName('clearMovie'))
            self.completePurchase(avId)

    def handleUnexpectedExit(self, avId):
        if (self.customerId == avId):
            taskMgr.remove(self.uniqueName('clearMovie'))
            toon = self.air.doTable.get(avId)

            if not toon:
                return

            if self.customerDNA:
                toon.b_setDNAString(self.customerDNA.makeNetString())

        if (self.busy == avId):
            self.sendClearMovie()

    def handleBootMessage(self, avId):
        if (self.customerId == avId):
            if self.customerDNA:
                toon = self.air.doTable.get(avId)

                if toon:
                    toon.b_setDNAString(self.customerDNA.makeNetString())

        self.sendClearMovie()