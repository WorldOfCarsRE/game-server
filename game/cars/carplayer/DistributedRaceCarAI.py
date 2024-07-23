from direct.distributed.DistributedObjectAI import DistributedObjectAI

class DistributedRaceCarAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.racingPoints: int = 0

    def setRacingPoints(self, racingPoints: int):
        self.racingPoints = racingPoints

    def getRacingPoints(self) -> int:
        return self.racingPoints

    def d_setRacingPoints(self, racingPoints: int):
        # TODO: Update API database
        self.sendUpdate('setRacingPoints', [racingPoints])

    def b_setRacingPoints(self, racingPoints: int):
        self.setRacingPoints(racingPoints)
        self.d_setRacingPoints(racingPoints)

    def addRacingPoints(self, deltaPoints: int):
        self.b_setRacingPoints(deltaPoints + self.getRacingPoints())
