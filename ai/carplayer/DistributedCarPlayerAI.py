from .DistributedCarAvatarAI import DistributedCarAvatarAI
from ai import ZoneConstants

class DistributedCarPlayerAI(DistributedCarAvatarAI):
    def __init__(self, air):
        DistributedCarAvatarAI.__init__(self, air)
        self.DISLname = ''
        self.DISLid = 0
        self.carCoins = 0

    def setDISLname(self, DISLname):
        self.DISLname = DISLname

    def getDISLname(self):
        return self.DISLname

    def setDISLid(self, DISLid):
        self.DISLid = DISLid

    def setCarCoins(self, carCoins: int):
        self.carCoins = carCoins

    def getCarCoins(self) -> int:
        return self.carCoins

    def announceGenerate(self):
        self.sendUpdateToAvatar(self.doId, 'setDISLname', [self.DISLname])
        self.sendUpdateToAvatar(self.doId, 'setRuleStates', [[[100, 1, 1, 1]]]) # To skip the tutorial, remove me to go to tutorial.
        self.sendUpdateToAvatar(self.doId, 'generateComplete', [])

    def sendEventLog(self, event: str, params: list, args: list):
        self.air.writeServerEvent(event, self.doId, f'{params}:{args}')

    def persistRequest(self, context: int):
        self.sendUpdateToAvatar(self.doId, 'persistResponse', [context, 1])

    def invokeRuleRequest(self, eventId: int, rules: list, context: int):
        print(f'invokeRuleRequest - {eventId} - {rules} - {context}')

        if eventId in ZoneConstants.MINIGAMES:
            level, score = rules

            self.d_updateCoins(score)
            self.sendUpdateToAvatar(self.doId, 'invokeRuleResponse', [eventId, rules, context])

    def d_updateCoins(self, coins: int):
        self.sendUpdateToAvatar(self.doId, 'setCarCoins', [coins])
