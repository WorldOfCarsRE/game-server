# from .DistributedFactoryAI import DistributedFactoryAI
from direct.showbase.DirectObject import DirectObject

class FactoryManagerAI(DirectObject):

    def __init__(self, air):
        DirectObject.__init__(self)
        self.air = air
        self.doId = 0

    def createFactory(self, factoryId, entranceId, players):
        factoryZone = self.air.allocateZone()
        # fact generation goes here
        return factoryZone