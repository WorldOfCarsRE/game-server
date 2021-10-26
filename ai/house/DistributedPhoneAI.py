from ai.house.DistributedFurnitureItemAI import DistributedFurnitureItemAI

class DistributedPhoneAI(DistributedFurnitureItemAI):

    def __init__(self, air, furnitureMgr, item):
        DistributedFurnitureItemAI.__init__(self, air, furnitureMgr, item)

    def setInitialScale(self):
        pass

    def getInitialScale(self):
        # TODO: I am lazy.
        return (1, 1, 1)