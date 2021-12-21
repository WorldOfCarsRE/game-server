from ai.toon import NPCToons
from ai.DistributedObjectAI import DistributedObjectAI
from direct.fsm.FSM import FSM
from typing import Dict

class TutorialBattleManager:
    pass

class DistributedBattleTutorialAI:
    pass

class DistributedTutorialInteriorAI(DistributedObjectAI):

    def __init__(self, air, zoneId, npcId, blockNumber = 0):
        DistributedObjectAI.__init__(self, air)
        self.zoneId = zoneId
        self.blockNumber = blockNumber
        self.npcId = npcId

    def getZoneIdAndBlock(self):
        return (self.zoneId, self.blockNumber)

    def getTutorialNpcId(self):
        return self.npcId

class TutorialInstance(FSM):

    def __init__(self, manager, avId):
        FSM.__init__(self, f'tutorial-object-{avId}')

        self.manager = manager
        self.air = self.manager.air
        self.avId = avId

        self.initializeTutorial()

    def cleanup(self):
        if self.tutorialTom:
            self.tutorialTom.requestDelete()

        del self.tutorialTom

        self.interior.requestDelete()
        del self.interior

        for zoneId in self.getZones():
            self.air.deallocateZone(zoneId)

    def initializeTutorial(self):
        self.branchZone = self.air.allocateZone()
        self.streetZone = self.air.allocateZone()
        self.shopZone = self.air.allocateZone()
        self.hqZone = self.air.allocateZone()

        self.tutorialTom = NPCToons.createNPC(self.air, 20000, self.shopZone, 0)
        self.tutorialTom.tutorial = True

        self.interior = DistributedTutorialInteriorAI(self.air, self.shopZone, self.tutorialTom.doId)
        self.interior.generateWithRequired(self.shopZone)

        hq = None

        suitPlanner = None

        self.flippy = None

        self.blackCatMgr = None

        self.manager.d_enterTutorial(
            self.avId,
            self.branchZone,
            self.streetZone,
            self.shopZone,
            self.hqZone
        )

    def getZones(self):
        return (
            self.branchZone,
            self.streetZone,
            self.shopZone,
            self.hqZone
        )

class TutorialManagerAI(DistributedObjectAI):
  # skipTutorialResponse(uint8);

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.tutorials: Dict[int] = {} # avId -> TutorialInstance

    def cleanup(self, avId):
        if avId in self.tutorials:
            self.tutorials[avId].cleanup()
            del self.tutorials[avId]

    def requestTutorial(self):
        avId = self.air.currentAvatarSender

        self.tutorials[avId] = TutorialInstance(self, avId)
        self.acceptOnce(self.air.getDeleteDoIdEvent(avId), self.cleanup, extraArgs = [avId])

    def d_enterTutorial(self, avId, branchZone, streetZone, shopZone, hqZone):
        self.sendUpdateToAvatar(avId, 'enterTutorial', [branchZone, streetZone, shopZone, hqZone])

    def rejectTutorial(self):
        pass

    def requestSkipTutorial(self):
        pass

    def allDone(self):
        pass

    def toonArrived(self):
        pass