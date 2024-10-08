from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.DistributedObjectAI import DistributedObjectAI

class OtpAvatarManagerAI(DistributedObjectAI):
    notify = directNotify.newCategory('OtpAvatarManagerAI')

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

    def delete(self):
        DistributedObjectAI.delete(self)

    def online(self):
        pass

    def requestAvatarList(self, todo0):
        pass

    def rejectAvatarList(self, todo0):
        pass

    def avatarListResponse(self, code):
        avId = self.air.getAvatarIdFromSender()

        self.sendUpdateToAvatarId(avId, 'avatarListResponse', [code])

    def requestAvatarSlot(self, todo0, todo1, todo2):
        pass

    def rejectAvatarSlot(self, todo0, todo1, todo2):
        pass

    def avatarSlotResponse(self, todo0, todo1):
        pass

    def requestPlayAvatar(self, todo0, todo1, todo2):
        pass

    def rejectPlayAvatar(self, todo0, todo1):
        pass

    def playAvatarResponse(self, todo0, todo1, todo2, todo3):
        pass

    def rejectCreateAvatar(self, todo0):
        pass

    def createAvatarResponse(self, todo0, todo1, todo2, todo3):
        pass

    def requestRemoveAvatar(self, todo0, todo1, todo2, todo3):
        pass

    def rejectRemoveAvatar(self, todo0):
        pass

    def removeAvatarResponse(self, todo0, todo1):
        pass

    def requestShareAvatar(self, todo0, todo1, todo2, todo3):
        pass

    def rejectShareAvatar(self, todo0):
        pass

    def shareAvatarResponse(self, todo0, todo1, todo2):
        pass
