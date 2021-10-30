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
        self.customerId = 0
        self.deletedTops: List[int] = []
        self.deletedBottoms: List[int] = []
        self.dummyToonAI = None

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

    def freeAvatar(self, avId):
        self.sendUpdateToAvatar(avId, 'freeAvatar', [])

    def d_setMovie(self, mode):
        self.sendUpdate('setMovie', [mode, self.occupied, globalClockDelta.getRealNetworkTime()])

    def d_setCustomerDNA(self, avId, dnaString):
        self.sendUpdate('setCustomerDNA', [avId, dnaString])

    def sendClearMovie(self):
        self.ignoreAll()
        self.customerDNA = None
        self.customerId = 0
        self.occupied = 0
        self.timedOut = 0

        self.d_setMovie(CLOSET_MOVIE_CLEAR)
        self.sendUpdate('setState', [0, 0, 0, '', [], []])
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
        self.sendClearMovie()

        return task.done

    def enterAvatar(self):
        avId = self.air.currentAvatarSender

        if self.occupied > 0:
            self.freeAvatar(avId)
            return

        av = self.air.doTable.get(avId)

        if not av:
            return

        self.customerDNA = ToonDNA()
        self.customerDNA.makeFromNetString(av.getDNAString())

        self.customerId = avId
        self.occupied = avId

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
        self.occupied = avId
        self.d_setMovie(CLOSET_MOVIE_COMPLETE)
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

                if which & SHIRT:
                    if av.replaceItemInClothesTopsList(newDNA.topTex,
                                                       newDNA.topTexColor,
                                                       newDNA.sleeveTex,
                                                       newDNA.sleeveTexColor,
                                                       self.customerDNA.topTex,
                                                       self.customerDNA.topTexColor,
                                                       self.customerDNA.sleeveTex,
                                                       self.customerDNA.sleeveTexColor) == 1:
                        av.b_setClothesTopsList(av.getClothesTopsList())

                if which & SHORTS:
                    if av.replaceItemInClothesBottomsList(newDNA.botTex,
                                                          newDNA.botTexColor,
                                                          self.customerDNA.botTex,
                                                          self.customerDNA.botTexColor) == 1:
                        av.b_setClothesBottomsList(av.getClothesBottomsList())

                self.finalizeDelete(avId)

            elif (finished == 1):
                if self.customerDNA:
                    av.b_setDNAString(self.customerDNA.makeNetString())

                    self.deletedTops = []
                    self.deletedBottoms = []
            else:
                self.sendUpdate('setCustomerDNA', [avId, blob])

        if (self.timedOut == 1 or finished == 0 or finished == 4):
            return

        if (self.occupied == avId):
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

        if (self.occupied == avId):
            self.sendClearMovie()

    def handleBootMessage(self, avId):
        if (self.customerId == avId):
            if self.customerDNA:
                toon = self.air.doTable.get(avId)

                if toon:
                    toon.b_setDNAString(self.customerDNA.makeNetString())

        self.sendClearMovie()

    def updateToonClothes(self, av, blob):
        # This is what the client has told us the new DNA should be
        proposedDNA = ToonDNA()
        proposedDNA.makeFromNetString(blob)

        # Don't completely trust the client. Enforce that only the clothes
        # change here. This eliminates the possibility of the gender, species, etc
        # of the toon changing, or a bug being exploited.
        updatedDNA = ToonDNA()
        updatedDNA.makeFromNetString(self.customerDNA.makeNetString())
        updatedDNA.topTex = proposedDNA.topTex
        updatedDNA.topTexColor = proposedDNA.topTexColor
        updatedDNA.sleeveTex = proposedDNA.sleeveTex
        updatedDNA.sleeveTexColor = proposedDNA.sleeveTexColor
        updatedDNA.botTex = proposedDNA.botTex
        updatedDNA.botTexColor = proposedDNA.botTexColor
        updatedDNA.torso = proposedDNA.torso

        av.b_setDNAString(updatedDNA.makeNetString())
        return updatedDNA

    def finalizeDelete(self, avId):
        av = self.air.doTable[avId]

        for top in self.deletedTops:
            av.removeItemInClothesTopsList(top[0], top[1], top[2], top[3])

        for bot in self.deletedBottoms:
            av.removeItemInClothesBottomsList(bot[0], bot[1])

        # empty the delete lists
        self.deletedTops = []
        self.deletedBottoms = []

        av.b_setClothesTopsList(av.getClothesTopsList())
        av.b_setClothesBottomsList(av.getClothesBottomsList())

class DistributedTrunkAI(DistributedClosetAI):

    def __init__(self, air, furnitureMgr, item):
        DistributedClosetAI.__init__(self, air, furnitureMgr, item)
        self.emptyLists()
        self.gender = ''

    def emptyLists(self):
        self.hatList: List[int] = []
        self.glassesList: List[int] = []
        self.backpackList: List[int] = []
        self.shoesList: List[int] = []
        self.removedItems: List[int] = []

    def enterAvatar(self):
        avId = self.air.currentAvatarSender

        if self.occupied > 0:
            self.freeAvatar(avId)
            return

        av = self.air.doTable.get(avId)

        if not av:
            return

        self.customerDNA = (av.getHat(), av.getGlasses(),
                            av.getBackpack(), av.getShoes())

        self.customerId = avId
        self.occupied = avId

        self.acceptOnce(self.air.getDeleteDoIdEvent(avId), self.handleUnexpectedExit, extraArgs = [avId])
        self.acceptOnce(f'bootAvFromEstate-{str(avId)}', self.handleBootMessage, extraArgs = [avId])

        if self.ownerId:
            self.ownerAv = None
            if self.ownerId in self.air.doTable:
                self.ownerAv = self.air.doTable[self.ownerId]

                self.hatList = self.ownerAv.getHatList()
                self.glassesList = self.ownerAv.getGlassesList()
                self.shoesList = self.ownerAv.getShoesList()
                self.gender = self.ownerAv.dna.gender

                self.__openTrunk()
            else:
                # TODO
                pass
        else:
            self.completePurchase(avId)

    def d_setState(self, mode):
        self.sendUpdate('setState', [mode, self.occupied, self.ownerId,
                                     self.gender, self.hatList, self.glassesList,
                                     self.backpackList, self.shoesList])

    def sendTimeoutMovie(self, task):
        pass

    def removeItem(self, id, tex, color, which):
        pass

    def __openTrunk(self):
        pass

    def setDNA(self, hatId, hatTex, hatColor, glassesId, glassesTex, glassesColor,
               backpackId, backpackTex, backpackColor, shoesId, shoesTex, shoesColor,
               finished, which):
        pass

    # i think we might need to override these from clothes, but idk
    def handleUnexpectedExit(self):
        pass

    def handleBootMessage(self):
        pass