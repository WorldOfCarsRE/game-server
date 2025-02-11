from direct.distributed.DistributedObjectAI import DistributedObjectAI

class DistributedRaceCarAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.racingPoints: int = 0
        self.animations: list = []
        self.consumables: list = []
        self.animations: list = []

    def setRacingPoints(self, racingPoints: int):
        self.racingPoints = racingPoints

    def getRacingPoints(self) -> int:
        return self.racingPoints

    def d_setRacingPoints(self, racingPoints: int):
        self.sendUpdate('setRacingPoints', [racingPoints])

    def b_setRacingPoints(self, racingPoints: int):
        self.setRacingPoints(racingPoints)
        self.d_setRacingPoints(racingPoints)

    def addRacingPoints(self, deltaPoints: int):
        self.b_setRacingPoints(deltaPoints + self.getRacingPoints())

    def setAnimations(self, animations: list):
        self.animations = animations
        if self.animations == []:
            self.animations = [21001, 21002, 21003, 21004, 21005, 21006, 21007]
            self.d_setAnimations(self.animations)

    def d_setAnimations(self, animations: list):
        self.sendUpdate('setAnimations', [animations])

    def getAnimations(self) -> list:
        return self.animations

    def setConsumables(self, consumables: list):
        self.consumables = consumables
        self.d_setConsumables(self.consumables)

    def d_setConsumables(self, consumables: list):
        self.sendUpdate('setConsumables', [consumables])

    def getConsumables(self) -> list:
        return self.consumables
    
    def setDetailings(self, detailings: list):
        self.detailings = detailings
        self.d_setDetailings(self.detailings)

    def d_setDetailings(self, detailings: list):
        self.sendUpdate('setDetailings', [detailings])

    def getDetailings(self) -> list:
        return self.detailings