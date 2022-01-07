from ai.building.DistributedElevatorExtAI import DistributedElevatorExtAI

class DistributedFactoryElevatorExtAI(DistributedElevatorExtAI):

    def __init__(self, air, bldg, factoryId, entranceId, antiShuffle = 0, minLaff = 0):
        DistributedElevatorExtAI.__init__(self, air, bldg, antiShuffle = antiShuffle, minLaff = minLaff)
        self.factoryId = factoryId
        self.entranceId = entranceId

    def getEntranceId(self):
        return self.entranceId

    def elevatorClosed(self):
        numPlayers = self.countFullSeats()
        if (numPlayers > 0):
            players = []
            for i in self.seats:
                if i not in [None, 0]:
                    players.append(i)
            factoryZone = self.bldg.createFactory(self.factoryId,
                                                  self.entranceId, players)
            
            for seatIndex in range(len(self.seats)):
                avId = self.seats[seatIndex]
                if avId:
                    self.sendUpdateToAvatar(avId, "setFactoryInteriorZone", [factoryZone])
                    self.clearFullNow(seatIndex)
        else:
            self.notify.warning("The elevator left, but was empty.")
        self.demand("Closed")

    def enterClosed(self):
        DistributedElevatorExtAI.enterClosed(self)
        self.demand('Opening')
        
    def sendAvatarsToDestination(self, avIdList):
        if (len(avIdList) > 0):
            factoryZone = self.bldg.createFactory(self.factoryId,
                                                  self.entranceId, avIdList)
            for avId in avIdList:
                if avId:
                    self.sendUpdateToAvatar(avId, 'setFactoryInteriorZoneForce', 
                                        [factoryZone])
