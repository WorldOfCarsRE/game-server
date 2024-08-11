from typing import List

from .DistributedCarAvatarAI import DistributedCarAvatarAI
from game.cars.zone import ZoneConstants

from .DistributedRaceCarAI import DistributedRaceCarAI

class DistributedCarPlayerAI(DistributedCarAvatarAI):
    def __init__(self, air):
        DistributedCarAvatarAI.__init__(self, air)
        self.DISLname = ''
        self.DISLid = 0
        self.carCoins = 0
        self.carCount = 0
        self.racecarId = 0
        self.animations = []
        self.racecar: DistributedRaceCarAI = None
        self.friendIds = []

    def setCars(self, carCount: int, cars: list):
        self.carCount = carCount
        self.racecarId = cars[0]

        if self.racecarId:
            # Retrieve their DistributedRaceCar object.
            self.racecar = self.air.readRaceCar(self.racecarId)

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

    def setAnimations(self, animations: list):
        self.animations = animations
        if self.animations == []:
            self.animations = [21001, 21002, 21003, 21004, 21005, 21006, 21007]
            self.d_setAnimations(self.animations)

    def d_setAnimations(self, animations: list):
        self.sendUpdate('setAnimations', [animations])

    def getAnimations(self) -> list:
        return self.animations

    def setCarCoins(self, carCoins: int):
        self.carCoins = carCoins

    def getCarCoins(self) -> int:
        return self.carCoins

    def d_setCarCoins(self, carCoins: int):
        self.sendUpdate('setCarCoins', [carCoins])

    def b_setCarCoins(self, carCoins: int):
        self.setCarCoins(carCoins)
        self.d_setCarCoins(carCoins)

    def announceGenerate(self):
        self.air.sendFriendManagerAccountOnline(self.DISLid)

        self.sendUpdateToAvatarId(self.doId, 'setRuleStates', [[[100, 1, 1, 1]]]) # To skip the tutorial, remove me to go to tutorial.
        self.sendUpdateToAvatarId(self.doId, 'generateComplete', [])

        self.air.incrementPopulation()

        # Fill in the missing information from the database (i.e. coins)
        self.air.fillInCarsPlayer(self)

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
            # level, score = rules

            # self.addCoins(score)

            self.addCoins(10)

        self.d_invokeRuleResponse(eventId, rules, context)

    def d_invokeRuleResponse(self, eventId: int, rules: List[int], context: int):
        self.sendUpdateToAvatarId(self.doId, 'invokeRuleResponse', [eventId, rules, context])

    def addCoins(self, deltaCoins: int):
        self.b_setCarCoins(deltaCoins + self.getCarCoins())
