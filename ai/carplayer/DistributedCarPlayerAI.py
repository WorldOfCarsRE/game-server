from .DistributedCarAvatarAI import DistributedCarAvatarAI

class DistributedCarPlayerAI(DistributedCarAvatarAI):
    def __init__(self, air):
        DistributedCarAvatarAI.__init__(self, air)

    def announceGenerate(self):
        self.sendUpdateToAvatar(self.air.currentAvatarSender, 'generateComplete', [])

    def sendEventLog(self, event: str, params, _):
        # self.air.writeServerEvent(event, self.doId, params)
        print(event, params, type(params), _, type(_))