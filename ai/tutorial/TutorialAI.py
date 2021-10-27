from ai.toon import NPCToons
from ai.DistributedObjectAI import DistributedObjectAI
from direct.fsm.FSM import FSM
from typing import Dict

class TutorialBattleManager:
    pass

class DistributedBattleTutorialAI:
    pass

class DistributedTutorialInteriorAI(DistributedObjectAI):

    def __init__(self, air, zoneId, blockNumber, npcId):
        DistributedObjectAI.__init__(self, air)
        self.zoneId = zoneId
        self.blockNumber = blockNumber
        self.npcId = npcId

    def getZoneIdAndBlock(self):
        return (self.zoneId, self.blockNumber)

    def getTutorialNpcId(self):
        return self.npcId

class TutorialBuildingAI:

    def __init__(self, air, extZone, interiorZone):
        pass

    def createTutorialNPC(self):
        npcId = 1436
        return npcId

class TutorialInstance(FSM):

    def __init__(self, avId):
        FSM.__init__(self, f'tutorial-object-{avId}')
        self.avId = avId
        self.initializeTutorial()

    def cleanup(self):
        pass

    def initializeTutorial(self):
        self.branchZone = self.air.allocateZone()
        self.streetZone = self.air.allocateZone()
        self.shopZone = self.air.allocateZone()
        self.hqZone = self.air.allocateZone()

        building = None
        hq = None

        suitPlanner = None

        self.flippy = None

        self.blackCatMgr = None

    def getZones(self):
        return (
            self.branchZone,
            self.streetZone,
            self.shopZone,
            self.hqZone
        )

class TutorialManagerAI(DistributedObjectAI):
  # skipTutorialResponse(uint8);
  # enterTutorial(uint32, uint32, uint32, uint32);

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.tutorials: Dict[TutorialInstance] = {}

    def requestTutorial(self):
        pass

    def rejectTutorial(self):
        pass

    def requestSkipTutorial(self):
        pass

    def allDone(self):
        pass

    def toonArrived(self):
        pass