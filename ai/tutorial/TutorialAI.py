from ai.toon import NPCToons
from ai.DistributedObjectAI import DistributedObjectAI

from direct.fsm.FSM import FSM
from direct.directnotify.DirectNotifyGlobal import directNotify

from typing import Dict

from ai.battle.BattleGlobals import Tracks

from ai.building.DistributedDoorAI import TALK_TO_TOM, UNLOCKED
from ai.building.DistributedDoorAI import DEFEAT_FLUNKY_TOM, DEFEAT_FLUNKY_HQ
from ai.building.DistributedDoorAI import GO_TO_PLAYGROUND, WRONG_DOOR_HQ

from ai.building.DistributedDoorAI import DistributedDoorAI

from ai.battle import DistributedBattleAI, DistributedSuitBaseAI

from ai.building.HQBuildingAI import HQBuildingAI
from ai.building import DoorTypes

from ai.LocalizerEnglish import TutorialHQOfficerName
from ai.quest import Quests

from ai.suit.DistributedSuitAI import SuitDNA
from ai.suit.SuitGlobals import SuitHeads

from panda3d.core import Point3, Vec3

class TutorialBattleManager:
    def __init__(self, avId):
        self.avId = avId

    def removeBattle(self, battle):
        if battle.suitsKilledThisBattle:
            if self.avId in simbase.air.tutorialManager.tutorials:
                simbase.air.tutorialManager.tutorials[self.avId].preparePlayerForHQ()
        battle.requestDelete()

class DistributedTutorialSuitAI(DistributedSuitBaseAI):
    notify = directNotify.newCategory('DistributedTutorialSuitAI')

    def __init__(self, air):
        DistributedSuitBaseAI.__init__(self, air)

    def destroy(self):
        del self.dna

    def createSuit(self, name, level):
        suitDNA = SuitDNA()
        suitDNA.head = name

        self.dna = suitDNA
        self.actualLevel = level

    def requestBattle(self, x, y, z, h, p, r):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)

        if not av:
            return

        self.confrontPos = Point3(x, y, z)
        self.confrontHpr = Vec3(h, p, r)

        if av.getBattleId() > 0:
            self.notify.warning(f'Avatar {avId} tried to request a battle, but is already in one.')
            self.b_setBrushOff(SuitDialog.getBrushOffIndex(self.getStyleName()))
            self.d_denyBattle(avId)
            return

        battle = DistributedBattleTutorialAI(self.air, TutorialBattleManager(avId), Vec3(35, 20, 0), self, avId, 20001)
        battle.tutorial = True
        battle.generateWithRequired(self.zoneId)

    def getConfrontPosHpr(self):
        return (self.confrontPos, self.confrontHpr)

class DistributedBattleTutorialAI(DistributedBattleAI):
    notify = directNotify.newCategory('DistributedBattleTutorialAI')

    def __init__(self, air, battleMgr, pos, suit, toonId, zoneId, finishCallback = None, maxSuits = 1):
        DistributedBattleAI.__init__(self, air, battleMgr, pos, suit, toonId, zoneId, finishCallback = finishCallback, maxSuits = maxSuits)

    def startRewardTimer(self):
        # There is no timer in the tutorial... The reward movie is random length.
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

        if self.hqHarry:
            self.hqHarry.requestDelete()

        del self.hqHarry

        self.hqBuilding.cleanup()
        del self.hqBuilding

        for zoneId in self.getZones():
            self.air.deallocateZone(zoneId)

    def initializeTutorial(self):
        self.branchZone = self.air.allocateZone()
        self.streetZone = self.air.allocateZone()
        self.shopZone = self.air.allocateZone()
        self.hqZone = self.air.allocateZone()

        self.tutorialTom = NPCToons.createNPC(self.air, 20000, None, self.shopZone, 0, self.preparePlayerForBattle)
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

        # Generate our HQ.
        hqHarryDesc = (self.hqZone, TutorialHQOfficerName, ('dls', 'ms', 'm', 'm', 6, 0, 6, 6, 0, 10, 0, 10, 2, 9), 'm', 1, 0)
        self.hqHarry = NPCToons.createNPC(self.air, 20002, hqHarryDesc, self.hqZone, 0, self.preparePlayerForTunnel)
        self.hqHarry.tutorial = True

        self.hqBuilding = HQBuildingAI(self.air, self.streetZone, self.hqZone, 1)

        # Leave our suit variable here.
        self.suit = None

        # Leave our flippy variable here.
        self.flippy = None

        # Leave our black cat manager variable here.
        self.blackCatMgr = None

        self.manager.d_enterTutorial(
            self.avId,
            self.branchZone,
            self.streetZone,
            self.shopZone,
            self.hqZone
        )

    def preparePlayerForBattle(self):
        self.interiorShopDoor.setDoorLock(UNLOCKED)

        # Generate our suit
        self.suit = DistributedTutorialSuitAI(self.air)
        self.suit.createSuit(SuitHeads.FLUNKY, 1)
        self.suit.generateWithRequired(self.streetZone)

        # Lock our doors
        self.exteriorShopDoor.setDoorLock(DEFEAT_FLUNKY_TOM)
        self.hqBuilding.door0.setDoorLock(DEFEAT_FLUNKY_HQ)

    def preparePlayerForHQ(self):
        if self.suit:
            self.suit.requestDelete()

        self.suit = None

        self.tutorialTom.requestDelete()
        self.tutorialTom = None

        self.exteriorShopDoor.setDoorLock(TALK_TO_HQ_TOM)

        self.hqBuilding.door0.setDoorLock(UNLOCKED)
        self.hqBuilding.insideDoor0.setDoorLock(TALK_TO_HQ)
        self.hqBuilding.insideDoor1.setDoorLock(TALK_TO_HQ)

    def preparePlayerForTunnel(self):
        self.flippy = NPCToons.createNPC(self.air, 20001, None, self.streetZone, 0)

        self.hqBuilding.insideDoor1.setDoorLock(UNLOCKED)
        self.hqBuilding.door1.setDoorLock(GO_TO_PLAYGROUND)
        self.hqBuilding.insideDoor0.setDoorLock(WRONG_DOOR_HQ)

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