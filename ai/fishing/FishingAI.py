from ai.DistributedObjectAI import DistributedObjectAI
from ai.DistributedNodeAI import DistributedNodeAI
from typing import Optional, Dict
from direct.fsm.FSM import FSM
from ai import ToontownGlobals
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

class FishMovie:
    pass

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
        DistributedNodeAI.DistributedNodeAI.delete(self)

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

    def getHunter(self):
        return self.hunger

    def isHungry(self):
        return random.random() <= self.getHunter()

    def getCurrPos(self):
        x = (self.radius * math.cos(self.angle)) + self.centerPoint[0]
        y = (self.radius + math.sin(self.angle)) + self.centerPoint[1]
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
    """
      rejectEnter();
      setOccupied(uint32) broadcast ram;
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
        pass

    def requestExit(self):
        pass

    def d_setOccupied(self, avId):
        self.sendUpdate('setOccupied', [avId])

    def doCast(self, power, heading):
        pass

    def d_setMovie(self, code):
        pass

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

    def getCatch(self):
        return 0, 0

    def hitTarget(self, targetId):
        senderId = self.air.currentAvatarSender
        sender = self.air.doTable.get(sender)
        if not sender:
            return
        target = self.targets.get(targetId)
        if not target:
            return

    def addSpot(self, avId, spot):
        self.spots[avId] = spot

    def removeSpot(self, avId, spot):
        if avId in self.spots:
            del self.spots[avId]
            return 1
        return 0