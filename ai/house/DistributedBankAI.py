from ai.house.DistributedFurnitureItemAI import DistributedFurnitureItemAI

BANK_MOVIE_CLEAR = 1
BANK_MOVIE_GUI = 2
BANK_MOVIE_DEPOSIT = 3
BANK_MOVIE_WITHDRAW = 4
BANK_MOVIE_NO_OP = 5
BANK_MOVIE_NOT_OWNER = 6
BANK_MOVIE_NO_OWNER = 7

class DistributedBankAI(DistributedFurnitureItemAI):

    def __init__(self, air, furnitureMgr, item):
        DistributedFurnitureItemAI.__init__(self, air, furnitureMgr, item)
        self.ownerId = furnitureMgr.house.avId
        self.occupied = 0

    def avatarEnter(self):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)
        if not av:
            return

        self.occupied = avId

        self.acceptOnce(self.air.getDeleteDoIdEvent(avId), self.handleExitedAvatar, extraArgs=[avId])
        # TODO: uhhhhhh can i get an order of booted avatar event please

        if self.ownerId:
            if self.ownerId == avId:
                self.d_setMovie(BANK_MOVIE_GUI)
            else:
                self.d_setMovie(BANK_MOVIE_NOT_OWNER)
                self.d_sendClearMovie()
        else:
            self.d_setMovie(BANK_MOVIE_NO_OWNER)
            self.d_sendClearMovie()

    def d_freeAvatar(self, avId):
        self.sendUpdateToAvatarId(avId, 'freeAvatar', [])

    def d_sendClearMovie(self):
        self.ignoreAll()
        self.occupied = 0
        self.d_setMovie(BANK_MOVIE_CLEAR)

    def d_setMovie(self, mode):
        self.sendUpdate('setMovie', [mode, self.occupied, globalClockDelta.getRealNetworkTime()])

    def handleExitedAvatar(self, avId):
        self.d_sendClearMovie()

    def transferMoney(self, amount):
        avId = self.air.currentAvatarSender
        if avId != self.occupied:
            return
        av = self.air.doTable.get(avId)
        if not av:
            self.d_sendClearMovie()
            return

        avMoney = av.getMoney()
        avMaxMoney = av.getMaxMoney()
        avBankMoney = av.getBankMoney()
        avMaxBankMoney = av.getMaxBankMoney()

        # TODO: should we move the non-movie logic to a bank-mgr ai?
        if amount > 0:
            if amount > avMoney:
                pass
            elif (amount + avBankMoney) > avMaxBankMoney:
                pass
            else:
                av.b_setMoney(avMoney - amount)
                av.b_setBankMoney(avBankMoney + amount)
            self.d_setMovie(BANK_MOVIE_DEPOSIT)
        elif amount < 0:
            if abs(amount) > avBankMoney:
                pass
            elif (abs(amount) + avMoney) > avMaxMoney:
                pass
            else:
                av.b_setMoney(avMoney - amount)
                av.b_setBankMoney(avBankMoney + amount)
            self.d_setMovie(BANK_MOVIE_WITHDRAW)
        else:
            self.d_setMovie(BANK_MOVIE_NO_OP)