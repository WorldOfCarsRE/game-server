from ai.DistributedObjectAI import DistributedObjectAI
from ai.DistributedNodeAI import DistributedNodeAI
from typing import Optional, Dict
from direct.fsm.FSM import FSM
from ai import ToontownGlobals
from ai.fishing import FishBase
import random
import math

class FishingTargetGlobals:
    OFF = 0
    MOVING = 1

    StepTime = 5.0
    MinimumHunger = 1.0

    NUM_TARGETS_INDEX = 0
    POS_START_INDEX = 1
    POS_END_INDEX = 4
    RADIUS_INDEX = 4
    WATER_LEVEL_INDEX = 5
    targetInfoDict = {
        ToontownGlobals.ToontownCentral : (2, -81, 31, -4.8, 14, -1.4),
        ToontownGlobals.SillyStreet : (2, 20, -664, -1.4, 14, (-1.4 - 0.438)),
        ToontownGlobals.LoopyLane : (2, -234, 175, -1.4, 14, (-1.4 - 0.462)),
        ToontownGlobals.PunchlinePlace : (2, 529, -70, -1.4, 13, (-1.4 - 0.486)),
        ToontownGlobals.DonaldsDock : (2, -17, 130, 1.730, 15, (1.730 - 3.615)),
        ToontownGlobals.BarnacleBoulevard : (2, 381, -350, -2, 14, (-2 - 0.482)),
        ToontownGlobals.SeaweedStreet : (2, -395, -226, -2, 14, (-2 - 0.482)),
        ToontownGlobals.LighthouseLane : (2, 350, 100, -2, 14, (-2 - 0.482)),
        ToontownGlobals.DaisyGardens : (2, 50, 47, -1.48, 13, (-1.48 - 0.345)),
        ToontownGlobals.ElmStreet : (2, 149, 44, -1.43, 13, (-1.43 - 0.618)),
        ToontownGlobals.MapleStreet : (2, 176, 100, -1.43, 13, (-1.43 - 0.618)),
        ToontownGlobals.OakStreet : (2, 134, -70.5, -1.5, 13, (-1.5 - 0.377)),
        ToontownGlobals.MinniesMelodyland : (2, -0.2, -20.2, -14.65, 14, (-14.65 - (-12))),
        ToontownGlobals.AltoAvenue : (2, -580, -90, -0.87, 14, (-0.87 - 1.844)),
        ToontownGlobals.BaritoneBoulevard : (2, -214, 250, -0.87, 14, (-0.87 - 1.844)),
        ToontownGlobals.TenorTerrace : (2, 715, -15, -0.87, 14, (-0.87 - 1.844)),
        ToontownGlobals.TheBrrrgh : (2, -58, -26, 1.7, 10, -0.8),
        ToontownGlobals.WalrusWay : (2, 460, 29, -2, 13, (-2 - 0.4)),
        ToontownGlobals.SleetStreet : (2, 340, 480, -2, 13, (-2 - 0.4)),
        ToontownGlobals.PolarPlace : (2, 45.5, 90.86, -2, 13, (-2 - 0.4)),
        ToontownGlobals.DonaldsDreamland : (2, 159, 0.2, -17.1, 14, (-17.1 - (- 14.6))),
        ToontownGlobals.LullabyLane : (2, 118, -185, -2.1, 14, (-2.1 - 0.378)),
        ToontownGlobals.PajamaPlace : (2, 241, -348, -2.1, 14, (-2.1 - 0.378)),
        ToontownGlobals.MyEstate : (3, 30,-126,-0.3, 16, -0.83),
    }

    def getNumTargets(zoneId):
        info = FishingTargetGlobals.targetInfoDict.get(zoneId)
        if info:
            return info[FishingTargetGlobals.NUM_TARGETS_INDEX]
        return 2

    def getTargetCenter(zoneId):
        info = FishingTargetGlobals.targetInfoDict.get(zoneId)
        if info:
            return info[FishingTargetGlobals.POS_START_INDEX:FishingTargetGlobals.POS_END_INDEX]
        return (0, 0, 0)

    def getTargetRadius(zoneId):
        info = FishingTargetGlobals.targetInfoDict.get(zoneId)
        if info:
            return info[FishingTargetGlobals.RADIUS_INDEX]
        return 10

    def getWaterLevel(zoneId):
        info = FishingTargetGlobals.targetInfoDict.get(zoneId)
        if info:
            return info[FishingTargetGlobals.WATER_LEVEL_INDEX]
        return 0

class FishMovies:
    NoMovie = 0
    EnterMovie = 1
    ExitMovie = 2
    CastMovie = 3
    PullInMovie = 4

class FishItems:
    Nothing = 0
    QuestItem = 1
    FishItem = 2
    JellybeanItem = 3
    BootItem = 4
    GagItem = 5
    OverTankLimit = 8
    FishItemNewEntry = 9
    FishItemNewRecord = 10
    item2Chance = {
      JellybeanItem: 100,
      FishItem: 0,
      BootItem: 0
    }
    """
    item2Chance = {
      FishItem: 93,
      JellybeanItem: 94,
      BootItem: 100,
    }
    """

class FishGlobals:
    FishingAngleMin = -50
    FishingAngleMax = 50
    ROD_WEIGHT_MIN_INDEX = 0
    ROD_WEIGHT_MAX_INDEX = 1
    ROD_CAST_COST_INDEX = 2
    rodDict = {
      0: (0, 4, 1),
      1: (0, 8, 2),
      2: (0, 12, 3),
      3: (0, 16, 4),
      4: (0, 20, 5),
    }
    rod2Jellybean = {
      0: 10,
      1: 20,
      2: 30,
      3: 75,
      4: 150
    }

    def getCastCost(rodId):
        return FishGlobals.rodDict[rodId][FishGlobals.ROD_CAST_COST_INDEX]

class DistributedFishingTargetAI(DistributedNodeAI, FSM):

    def __init__(self, air, pond, hunger):
        DistributedNodeAI.__init__(self, air)
        FSM.__init__(self, self.__class__.__name__)
        self.stateIndex = FishingTargetGlobals.OFF
        self.pond = pond
        self.area = pond.getArea()
        self.area = self.pond.getArea()
        self.hunger = hunger
        self.centerPoint = FishingTargetGlobals.getTargetCenter(self.area)
        self.maxRadius = FishingTargetGlobals.getTargetRadius(self.area)
        self.hunger = hunger
        self.angle = 0.0
        self.radius = 0.0
        self.time = 0.0

    def generate(self):
        DistributedNodeAI.generate(self)
        self.stateIndex = FishingTargetGlobals.MOVING
        self.demand('Moving')

    def delete(self):
        taskMgr.remove(self.getMovingTask())
        del self.pond
        DistributedNodeAI.delete(self)

    def getPondDoId(self):
        return self.pond.getDoId()

    def getMovingTask(self):
        return self.uniqueName('moveFishingTarget')

    def enterMoving(self):
        self.moveFishingTarget()

    def exitMoving(self):
        taskMgr.remove(self.getMovingTask())

    def getState(self):
        return [self.stateIndex, self.angle, self.radius, self.time,
                globalClockDelta.getRealNetworkTime()]

    def d_setState(self, stateIndex, angle, radius, time):
        self.sendUpdate('setState', [stateIndex, angle, radius, time,
                                     globalClockDelta.getRealNetworkTime()])

    def getHungry(self):
        return self.hunger

    def isHungry(self):
        return random.random() <= self.getHungry()

    def getCurrPos(self):
        x = (self.radius * math.cos(self.angle)) + self.centerPoint[0]
        y = (self.radius * math.sin(self.angle)) + self.centerPoint[1]
        z = self.centerPoint[2]
        return (x, y, z)

    def moveFishingTarget(self, task=None):
        self.d_setPos(*self.getCurrPos())
        self.angle = random.random() * 360.0
        self.radius = random.random() * self.maxRadius
        self.time = 6.0 + (6.0 * random.random())
        self.d_setState(self.stateIndex, self.angle, self.radius, self.time)
        waitTime = 1.0 + random.random() * 4.0
        taskMgr.doMethodLater(self.time + waitTime,
                              self.moveFishingTarget,
                              self.getMovingTask())

class DistributedFishingSpotAI(DistributedObjectAI):
    TIMEOUT = 45.0
    """
      sellFishComplete(uint8, uint16);
    """

    def __init__(self, air, pond, posHpr):
        DistributedObjectAI.__init__(self, air)
        self.posHpr = posHpr
        self.avId = 0
        self.timeoutTask = None
        self.pond = pond

    def delete(self):
        DistributedObjectAI.DistributedObjectAI.delete(self)

    def getPondDoId(self):
        return self.pond.getDoId()

    def getPosHpr(self):
        return self.posHpr

    def requestEnter(self):
        senderId = self.air.currentAvatarSender
        if self.avId == senderId:
            return
        # if not ToontownAccessAI.canAccess(avId, self.zoneId):
        # self.sendUpdateToAvatarId(avId, 'rejectEnter', [])
        # return
        if self.avId:
            self.sendUpdateToAvatarId(senderId, 'rejectEnter', [])
        else:
            self.avId = senderId
            self.pond.addSpot(senderId, self)
            self.acceptOnce(self.air.getAvatarExitEvent(senderId), self.__handleUnexpectedEvent)
            self.__stopTimeout()
            self.d_setOccupied(self.avId)
            self.d_setMovie(FishMovies.EnterMovie)
            self.__startTimeout(self.TIMEOUT)


    def requestExit(self):
        senderId = self.air.currentAvatarSender
        if self.avId != senderId:
            return
        self.normalExit()

    def __startTimeout(self, timeLimit):
        self.__stopTimeout()
        self.timeoutTask = taskMgr.doMethodLater(timeLimit,
                                                 self.normalExit,
                                                 self.uniqueName('timeout'))

    def __stopTimeout(self):
        if self.timeoutTask:
            taskMgr.remove(self.timeoutTask)
            self.timeoutTask = None

    def cleanupAvatar(self):
        self.pond.removeSpot(self.avId, self)
        self.ignore(self.air.getAvatarExitEvent(self.avId))
        self.__stopTimeout()
        self.avId = 0

    def normalExit(self, task=None):
        self.cleanupAvatar()
        self.d_setMovie(FishMovies.ExitMovie)
        taskMgr.doMethodLater(1.2, self.__clearEmpty,
                              self.uniqueName('clearEmpty'))

    def __clearEmpty(self, task=None):
        self.d_setOccupied(0)

    def __handleUnexpectedEvent(self):
        self.cleanupAvatar()
        self.d_setOccupied(0)

    def d_setOccupied(self, avId):
        self.sendUpdate('setOccupied', [avId])

    def doCast(self, power, heading):
        senderId = self.air.currentAvatarSender
        if self.avId != senderId:
            return
        if power <= 0 or power > 1:
            return

        if heading < FishGlobals.FishingAngleMin:
            return
        if heading > FishGlobals.FishingAngleMax:
            return

        sender = self.air.doTable.get(senderId)
        if not sender:
            return

        self.__stopTimeout()
        money = sender.getMoney()
        castCost = FishGlobals.getCastCost(sender.getFishingRod())

        if money < castCost:
            self.normalExit()
            return

        sender.b_setMoney(money - castCost)
        self.d_setMovie(FishMovies.CastMovie, power=power, h=heading)
        self.__startTimeout(self.TIMEOUT)

    def hitTarget(self, code, item):
        if code == FishItems.JellybeanItem:
            self.d_setMovie(FishMovies.PullInMovie, code=code, itemDesc1=item)
        self.__startTimeout(self.TIMEOUT)

    def d_setMovie(self, mode, code=0, itemDesc1=0, itemDesc2=0, itemDesc3=0, power=0, h=0):
        self.sendUpdate('setMovie', [mode, code, itemDesc1, itemDesc2, itemDesc3, power, h])

    def sellFish(self):
        pass

class DistributedFishingPondAI(DistributedObjectAI):

    def __init__(self, air, area):
        DistributedObjectAI.__init__(self, air)
        self.area = area
        self.targets: Optional[Dict[DistributedFishingTargetAI]] = {}
        self.spots: Dict[int] = {}

    def getArea(self):
        return self.area

    def getDoId(self):
        return self.do_id

    def generate(self):
        DistributedObjectAI.generate(self)
        for i in range(FishingTargetGlobals.getNumTargets(self.getArea())):
            hunger = FishingTargetGlobals.MinimumHunger + \
                     random.random() * (1-FishingTargetGlobals.MinimumHunger)
            target = DistributedFishingTargetAI(self.air, self, hunger)
            target.generateWithRequired(self.zoneId)
            self.targets[target.do_id] = target

    def delete(self):
        for target in self.targets.values():
            target.requestDelete()
        self.targets = Optional[Dict[DistributedFishingTargetAI]] = None
        DistributedObjectAI.DistributedObjectAI.delete(self)

    def getCatch(self, av):
        itemType = FishItems.BootItem
        value = None
        rodId = av.getFishingRod()

        # TODO: prioritize quest items
        randNum = random.randint(0, 100)
        for item, chance in FishItems.item2Chance.items():
            if randNum <= chance:
                itemType = item
                break

        if itemType == FishItems.FishItem:
            pass
        elif itemType == FishItems.BootItem:
            pass
        elif itemType == FishItems.JellybeanItem:
            value = FishGlobals.rod2Jellybean[rodId]
            av.addMoney(value)

        return itemType, value

    def hitTarget(self, targetId):
        senderId = self.air.currentAvatarSender
        sender = self.air.doTable.get(senderId)
        if not sender:
            return
        spot = self.spots.get(senderId)
        if not spot:
            return
        target = self.targets.get(targetId)
        if not target:
            return
        if target.isHungry():
            code, item = self.getCatch(sender)
            spot.hitTarget(code, item)

    def addSpot(self, avId, spot):
        self.spots[avId] = spot

    def removeSpot(self, avId, spot):
        if avId in self.spots:
            del self.spots[avId]
            return 1
        return 0