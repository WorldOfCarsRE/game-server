from ai.toon import NPCToons
from ai.DistributedObjectAI import DistributedObjectAI
from direct.fsm.FSM import FSM
from typing import Dict
from ai.battle.BattleGlobals import Tracks
from ai.building.DistributedDoorAI import TALK_TO_TOM, DistributedDoorAI
from ai.building import DoorTypes

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

        self.exteriorShopDoor.requestDelete()
        del self.exteriorShopDoor

        self.interiorShopDoor.requestDelete()
        del self.interiorShopDoor

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

        self.exteriorShopDoor = DistributedDoorAI(self.air, 2, DoorTypes.EXT_STANDARD, doorIndex = 0)
        self.exteriorShopDoor.generateWithRequired(self.streetZone)
        self.interiorShopDoor = DistributedDoorAI(self.air, 0, DoorTypes.INT_STANDARD, doorIndex = 0)
        self.interiorShopDoor.setDoorLock(TALK_TO_TOM)
        self.interiorShopDoor.generateWithRequired(self.shopZone)
        self.exteriorShopDoor.setOtherDoor(self.interiorShopDoor)
        self.interiorShopDoor.setOtherDoor(self.exteriorShopDoor)

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
        avId = self.air.currentAvatarSender

        # Make sure the avatar exists
        av = self.air.doTable.get(avId)

        if av:
            # Acknowlege that the player has seen a tutorial
            self.air.writeServerEvent('finishedTutorial', avId, '')
            av.b_setTutorialAck(1)

            self.sendUpdateToAvatar(avId, 'skipTutorialResponse', [1])

    def requestSkipTutorial(self):
        pass

    def allDone(self):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)

        if av:
            av.b_setTutorialAck(1)

        self.cleanup(avId)
        self.ignore(self.air.getAvatarExitEvent(avId))

    def toonArrived(self):
        avId = self.air.currentAvatarSender

        # Make sure the avatar exists
        av = self.air.doTable.get(avId)

        # Clear out the avatar's quests, hp, inventory, and everything else in case
        # he made it half way through the tutorial last time.
        if av:
            # No quests
            av.b_setQuests([])
            av.b_setQuestHistory([])
            av.b_setRewardHistory(0, [])
            av.b_setQuestCarryLimit(1)
            # Starting HP
            av.b_setMaxHp(15)
            av.b_setHp(15)
            # No exp
            av.experience.zeroOutExp()
            av.d_setExperience(av.experience.makeNetString())
            # One cupcake and one squirting flower
            av.inventory.zero()
            av.inventory.addItems(Tracks.THROW, 0, 1)
            av.inventory.addItems(Tracks.SQUIRT, 0, 1)
            av.d_setInventory(av.inventory.makeNetString())
            # No cogs defeated
            av.b_setCogStatus([1] * 32)
            av.b_setCogCount([0] * 32)