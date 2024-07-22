from typing import List

from .DistributedCarAvatarAI import DistributedCarAvatarAI
from ai import ZoneConstants

class DistributedCarPlayerAI(DistributedCarAvatarAI):
    def __init__(self, air):
        DistributedCarAvatarAI.__init__(self, air)
        self.DISLname = ''
        self.DISLid = 0
        self.carCoins = 0
        self.carCount = 0
        self.racecarId = 0
        self.friendIds = []

    def setCars(self, carCount: int, cars: list):
        self.carCount = carCount
        self.racecarId = cars[0]

    def getRaceCarId(self) -> int:
        return self.racecarId

    def setDISLname(self, DISLname: str):
        self.DISLname = DISLname

    def getDISLname(self) -> str:
        return self.DISLname

    def setDISLid(self, DISLid: int) -> int:
        self.DISLid = DISLid

    def getDISLid(self) -> int:
        return self.DISLid

    def setCarCoins(self, carCoins: int):
        self.carCoins = carCoins

    def getCarCoins(self) -> int:
        return self.carCoins

    def announceGenerate(self):
        self.air.sendFriendManagerAccountOnline(self.DISLid)

        self.sendUpdateToAvatarId(self.doId, 'setRuleStates', [[[100, 1, 1, 1]]]) # To skip the tutorial, remove me to go to tutorial.
        self.sendUpdateToAvatarId(self.doId, 'generateComplete', [])

        self.air.incrementPopulation()

    def delete(self):
        # TODO: Set a post-remove message in case of an AI crash.
        self.air.sendFriendManagerAccountOffline(self.DISLid)

        self.air.decrementPopulation()

        DistributedCarAvatarAI.delete(self)

    def sendEventLog(self, event: str, params: list, args: list):
        self.air.writeServerEvent(event, self.doId, f'{params}:{args}')

    def persistRequest(self, context: int):
        self.sendUpdateToAvatarId(self.doId, 'persistResponse', [context, 1])

    def invokeRuleRequest(self, eventId: int, rules: list, context: int):
        print(f'invokeRuleRequest - {eventId} - {rules} - {context}')

        if eventId in ZoneConstants.MINIGAMES:
            level, score = rules

            self.addCoins(score)

        self.d_invokeRuleResponse(eventId, rules, context)

    def d_invokeRuleResponse(self, eventId: int, rules: List[int], context: int):
        self.sendUpdateToAvatarId(self.doId, 'invokeRuleResponse', [eventId, rules, context])

    def addCoins(self, deltaCoins: int):
        self.sendUpdate('setCarCoins', [deltaCoins + self.getCarCoins()])
