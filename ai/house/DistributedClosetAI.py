from ai.house.DistributedFurnitureItemAI import DistributedFurnitureItemAI

class DistributedClosetAI(DistributedFurnitureItemAI):

    def __init__(self, air, furnitureMgr, item):
        DistributedFurnitureItemAI.__init__(self, air, furnitureMgr, item)
        self.ownerId = self.furnitureMgr.house.avId

    def setOwnerId(self):
        pass

    def getOwnerId(self):
        return self.ownerId