from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.DistributedObjectGlobalAI import DistributedObjectGlobalAI

class CentralLoggerAI(DistributedObjectGlobalAI):
    notify = directNotify.newCategory('CentralLoggerAI')
    notify.setInfo(True)

    def sendMessage(self, category, message, targetDISLid, targetAvId):
        self.sendUpdate('sendMessage', [category, message, targetDISLid, targetAvId])

    def sendMessage(self, category, message, targetDISLid, targetAvId):
        self.notify.debug('Received message from client')

    def logAIGarbage(self):
        pass
