from ai.DistributedObjectAI import DistributedObjectAI

class DistributedMailboxAI(DistributedObjectAI):

    def __init__(self, air, house):
        DistributedObjectAI.__init__(self, air)

        self.house = house

    def getHouseId(self):
        return self.house.do_id

    def getHousePos(self):
        return self.house.housePos

    def getName(self):
        return self.house.name

    def avatarEnter(self):
        avId = self.air.currentAvatarSender
        self.sendUpdateToAvatar(avId, 'freeAvatar', [])