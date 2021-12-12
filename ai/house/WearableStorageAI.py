from ai.house.DistributedFurnitureItemAI import DistributedFurnitureItemAI
from ai.toon.DistributedToonAI import DistributedToonAI
from ai.toon import ToonDNA
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
        self.customerDNA = None
        self.occupied = 0
        self.deletedTops: List[int] = []
        self.deletedBottoms: List[int] = []
        self.dummyToonAI = None

    def delete(self):
        self.ignoreAll()
        self.customerDNA = None
        self.occupied = 0
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
        av = self.air.doTable.get(self.occupied)

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

        self.customerDNA = ToonDNA.ToonDNA()
        self.customerDNA.makeFromNetString(av.getDNAString())

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

        self.sendUpdate('setState', [OPEN, self.occupied, self.ownerav.doId, self.ownerAv.dna.gender, topList, botList])

        taskMgr.doMethodLater(TIMEOUT_TIME, self.sendTimeoutMovie, self.uniqueName('clearMovie'))

    def completePurchase(self, avId):
        self.occupied = avId
        self.d_setMovie(CLOSET_MOVIE_COMPLETE)
        self.sendClearMovie()

    def removeItem(self, trashBlob, which):
        pass

    def setDNA(self, blob, finished, which):
        avId = self.air.currentAvatarSender

        if avId != self.occupied:
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
        if (self.occupied == avId):
            taskMgr.remove(self.uniqueName('clearMovie'))
            toon = self.air.doTable.get(avId)

            if not toon:
                return

            if self.customerDNA:
                toon.b_setDNAString(self.customerDNA.makeNetString())

        if (self.occupied == avId):
            self.sendClearMovie()

    def handleBootMessage(self, avId):
        if (self.occupied == avId):
            if self.customerDNA:
                toon = self.air.doTable.get(avId)

                if toon:
                    toon.b_setDNAString(self.customerDNA.makeNetString())

        self.sendClearMovie()

    def updateToonClothes(self, av, blob):
        # This is what the client has told us the new DNA should be
        proposedDNA = ToonDNA.ToonDNA()
        proposedDNA.makeFromNetString(blob)

        # Don't completely trust the client. Enforce that only the clothes
        # change here. This eliminates the possibility of the gender, species, etc
        # of the toon changing, or a bug being exploited.
        updatedDNA = ToonDNA.ToonDNA()
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

        self.occupied = avId

        self.acceptOnce(self.air.getDeleteDoIdEvent(avId), self.handleUnexpectedExit, extraArgs = [avId])
        self.acceptOnce(f'bootAvFromEstate-{str(avId)}', self.handleBootMessage, extraArgs = [avId])

        if self.ownerId:
            self.ownerAv = None
            if self.ownerId in self.air.doTable:
                self.ownerAv = self.air.doTable[self.ownerId]

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

    def d_clearCustomerDNA(self):
        self.sendUpdate('setCustomerDNA', [0 for x in range(14)])

    def sendTimeoutMovie(self, task):
        self.timedOut = 1
        self.d_setMovie(CLOSET_MOVIE_TIMEOUT)
        self.sendClearMovie()

        return task.done

    def removeItem(self, id, tex, color, which):
        pass

    def __openTrunk(self):
        self.hatList = self.ownerAv.getHatList()
        self.glassesList = self.ownerAv.getGlassesList()
        self.shoesList = self.ownerAv.getShoesList()
        self.gender = self.ownerAv.dna.gender

        self.d_setState(OPEN)

        taskMgr.doMethodLater(TIMEOUT_TIME, self.sendTimeoutMovie, self.uniqueName('clearMovie'))

    def setDNA(self, hatId, hatTex, hatColor, glassesId, glassesTex, glassesColor,
               backpackId, backpackTex, backpackColor, shoesId, shoesTex, shoesColor,
               finished, which):

        avId = self.air.currentAvatarSender

        if avId != self.occupied:
            return

        if avId in self.air.doTable:
            av = self.air.doTable[avId]

            hat = (hatId, hatTex, hatColor)
            glasses = (glassesId, glassesTex, glassesColor)
            backpack = (backpackId, backpackTex, backpackColor)
            shoes = (shoesId, shoesTex, shoesColor)

            if not av.checkAccessorySanity(ToonDNA.HAT, hat[0], hat[1], hat[2]):
                return
            if not av.checkAccessorySanity(ToonDNA.GLASSES, glasses[0], glasses[1], glasses[2]):
                return
            if not av.checkAccessorySanity(ToonDNA.BACKPACK, backpack[0], backpack[1], backpack[2]):
                return
            if not av.checkAccessorySanity(ToonDNA.SHOES, shoes[0], shoes[1], shoes[2]):
                return

            if not finished:
                self.sendUpdate('setCustomerDNA',
                                [avId, hatId, hatTex, hatColor, glassesId, glassesTex, glassesColor,
                                 backpackId, backpackTex, backpackColor, shoesId, shoesTex, shoesColor, which])
                return

            if finished == 1: # Cancel
                self.handleCleanFinish()
            else: # Finished
                if avId != self.ownerId:
                    return

                if which & ToonDNA.HAT:
                    avHat = av.getHat()
                    if av.replaceItemInAccessoriesList(ToonDNA.HAT, avHat[0], avHat[1], avHat[2], hat[0], hat[1], hat[2]):
                        av.b_setHat(*hat)

                if which & ToonDNA.GLASSES:
                    avGlasses = av.getGlasses()
                    if av.replaceItemInAccessoriesList(ToonDNA.GLASSES, avGlasses[0], avGlasses[1], avGlasses[2], glasses[0], glasses[1], glasses[2]):
                        av.b_setGlasses(*glasses)

                if which & ToonDNA.BACKPACK:
                    avBackpack = av.getBackpack()
                    if av.replaceItemInAccessoriesList(ToonDNA.BACKPACK, avBackpack[0], avBackpack[1], avBackpack[2], backpack[0], backpack[1], backpack[2]):
                        av.b_setBackpack(*backpack)

                if which & ToonDNA.SHOES:
                    avShoes = av.getShoes()
                    if av.replaceItemInAccessoriesList(ToonDNA.SHOES, avShoes[0], avShoes[1], avShoes[2], shoes[0], shoes[1], shoes[2]):
                        av.b_setShoes(*shoes)

                for item in self.removedItems[:]:
                    self.removedItems.remove(item)
                    av.removeItemInAccessoriesList(*item)

                av.b_setHatList(av.getHatList())
                av.b_setGlassesList(av.getGlassesList())
                av.b_setBackpackList(av.getBackpackList())
                av.b_setShoesList(av.getShoesList())

                self.handleCleanFinish()

            self.ignoreAll()

    def handleCleanFinish(self):
        self.customerDNA = None
        self.gender = ''
        self.emptyLists()
        self.d_setMovie(CLOSET_MOVIE_COMPLETE)
        self.occupied = 0
        self.d_setMovie(CLOSET_MOVIE_CLEAR)
        self.d_clearCustomerDNA()
        self.d_setState(CLOSED)

    def handleUnexpectedExit(self, avId):
        if avId != self.occupied:
            return

        self.occupied = 0
        self.customerDNA = None
        self.gender = ''
        self.emptyLists()
        self.d_setMovie(CLOSET_MOVIE_CLEAR)
        self.d_clearCustomerDNA()
        self.d_setState(CLOSED)

    def handleBootMessage(self):
        pass