from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.directnotify.DirectNotifyGlobal import directNotify

class MagicWordManagerAI(DistributedObjectAI):
    notify = directNotify.newCategory('MagicWordManagerAI')

    def setMagicWord(self, magicWord, avId, zoneId):
        invokerId = self.air.getAvatarIdFromSender()
        invoker = self.air.doId2do.get(invokerId)

        if not invoker:
            self.sendUpdateToAvatarId(invokerId, 'setMagicWordResponse', ['Missing invoker!'])
            return

        target = self.air.doId2do.get(avId)

        if not target:
            self.sendUpdateToAvatarId(invokerId, 'setMagicWordResponse', ['Missing target!'])
            return

    def setWho(self, avIds = []):
        avId = self.air.getAvatarIdFromSender()
        av = self.air.doId2do.get(avId)

        if not avId:
            return

        self.sendUpdateToAvatarId(avId, 'setWho', [avIds])
