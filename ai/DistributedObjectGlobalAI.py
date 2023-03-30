from .DistributedObjectAI import DistributedObjectAI

class DistributedObjectGlobalAI(DistributedObjectAI):
    def announceGenerate(self):
        DistributedObjectAI.announceGenerate(self)
        self.air.registerForChannel(self.doId)

    def generateGlobalObject(self, zoneId = 2):
        if not self.doId:
            raise Exception('doId not set for global object')
        self.air.doTable[self.doId] = self
        self.location = (self.parentId, zoneId)
        self.queueUpdates = False
        self.generate()
        self.announceGenerate()

    def delete(self):
        self.air.unregisterForChannel(self.doId)
        DistributedObjectAI.delete(self)
