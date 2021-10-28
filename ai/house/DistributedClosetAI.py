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

    def delete(self):
        self.ignoreAll()
        self.customerDNA = None
        self.customerId = None
        del self.deletedTops
        del self.deletedBottoms

    def handleExitedAvatar(self, avId):
        self.d_sendClearMovie()

    def getOwnerId(self):
        return self.ownerId

    def d_freeAvatar(self, avId):
        self.sendUpdateToAvatar(avId, 'freeAvatar', [])

    def d_setMovie(self, mode):
        self.sendUpdate('setMovie', [mode, self.occupied, globalClockDelta.getRealNetworkTime()])
        self.d_sendClearMovie(None)

    def d_setCustomerDNA(self, avId, dnaString):
        self.sendUpdate('setCustomerDNA', [avId, dnaString])

    def d_sendClearMovie(self):
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

    def d_sendTimeoutMovie(self, task):
        av = self.air.doTable.get(self.customerId)
        if av != None and self.customerDNA:
            av.b.setDNAString(self.customerDNA.makeNetString())

        self.timedOut = 1
        self.d_setMovie(CLOSET_MOVIE_TIMEOUT)
        self.d_sendClearMovie()      

        return task.done

    def enterAvatar(self):
        pass

    def removeItem(self, trashBlob, which):
        pass

    def setDNA(self, blob, finished, which):
        pass

