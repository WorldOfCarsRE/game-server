from ai.DistributedObjectAI import DistributedObjectAI
from ai.DistributedNodeAI import DistributedNodeAI
from typing import Optional, Dict, NamedTuple
from direct.fsm.FSM import FSM
from ai import ToontownGlobals
from ai.fishing.FishBase import FishBase
from ai.fishing.FishCollectionEnum import *
import random
import math
import copy

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
      FishItem: 93,
      JellybeanItem: 94,
      BootItem: 100,
    }

class FishingRod(NamedTuple):
    weightMin: int
    weightMax: int
    rarity: float
    castCost: int
    jellybeanReward: int

class FishProperties(NamedTuple):
    weightMin: int
    weightMax: int
    rarity: int
    zoneList: tuple

class RarityHandler:

    def getEffectiveRarity(rarity, maxRarity, offset):
        if rarity + (offset) > maxRarity:
            return maxRarity
        return rarity + (offset)

class WeightHandler:

    def getWeightRange(fishes, genus, species):
        fishInfo = fishes[genus][species]
        return (fishInfo.weightMin, fishInfo.weightMax)

    def getRodWeightRange(rodDict, rodIndex):
        rodProps = rodDict[rodIndex]
        return (rodProps.weightMin, rodProps.weightMax)

    def canBeCaughtByRod(fishes, rodDict, genus, species, rodIndex):
        minFishWeight, maxFishWeight = WeightHandler.getWeightRange(fishes, genus, species)
        minRodWeight, maxRodWeight = WeightHandler.getRodWeightRange(rodDict, rodIndex)
        if ((minRodWeight <= maxFishWeight) and
            (maxRodWeight >= minFishWeight)):
            return 1
        return 0

class RodHandler:
    globalRarityDialBase = 4.3
    rodDict = {
      0: FishingRod(weightMin=0, weightMax=4, rarity=(1.0 / (globalRarityDialBase * 1)),
                    castCost=1, jellybeanReward=10),
      1: FishingRod(weightMin=0, weightMax=8, rarity=(1.0 / (globalRarityDialBase * 1)),
                    castCost=2, jellybeanReward=20),
      2: FishingRod(weightMin=0, weightMax=12, rarity=(1.0 / (globalRarityDialBase * 1)),
                    castCost=3, jellybeanReward=30),
      3: FishingRod(weightMin=0, weightMax=16, rarity=(1.0 / (globalRarityDialBase * 1)),
                    castCost=4, jellybeanReward=75),
      4: FishingRod(weightMin=0, weightMax=20, rarity=(1.0 / (globalRarityDialBase * 1)),
                    castCost=5, jellybeanReward=150),
    }

    def getRodDict():
        return RodHandler.rodDict

    def getRarity(rodId):
        return RodHandler.getRodDict()[rodId].rarity

    def getCastCost(rodId):
        return RodHandler.getRodDict()[rodId].castCost

    def getJellybeanReward(rodId):
        return RodHandler.getRodDict()[rodId].jellybeanReward

class FishGlobals:
    MAX_RARITY = 10
    FishingAngleMin = -50
    FishingAngleMax = 50
    Anywhere = 1
    TTG = ToontownGlobals
    FISHES = {
      0: ( FishProperties(weightMin=1, weightMax=3, rarity=1, zoneList=(Anywhere,)),
           FishProperties(weightMin=1, weightMax=1, rarity=4, zoneList=(TTG.ToontownCentral, Anywhere)),
           FishProperties(weightMin=3, weightMax=5, rarity=5, zoneList=(TTG.PunchlinePlace, TTG.TheBrrrgh)),
           FishProperties(weightMin=3, weightMax=5, rarity=3, zoneList=(TTG.SillyStreet, TTG.DaisyGardens)),
           FishProperties(weightMin=1, weightMax=5, rarity=2, zoneList=(TTG.LoopyLane, TTG.ToontownCentral)),
          ),
      2: ( FishProperties(weightMin=2, weightMax=6, rarity=1, zoneList=(TTG.DaisyGardens, Anywhere)),
           FishProperties(weightMin=2, weightMax=6, rarity=9, zoneList=(TTG.ElmStreet, TTG.DaisyGardens)),
           FishProperties(weightMin=5, weightMax=11, rarity=4, zoneList=(TTG.LullabyLane,)),
           FishProperties(weightMin=2, weightMax=6, rarity=3, zoneList=(TTG.DaisyGardens, TTG.MyEstate)),
           FishProperties(weightMin=5, weightMax=11, rarity=2, zoneList=(TTG.DonaldsDreamland, TTG.MyEstate)),
          ),
      4: ( FishProperties(weightMin=2, weightMax=8, rarity=1, zoneList=(TTG.ToontownCentral, Anywhere,)),
           FishProperties(weightMin=2, weightMax=8, rarity=4, zoneList=(TTG.ToontownCentral, Anywhere)),
           FishProperties(weightMin=2, weightMax=8, rarity=2, zoneList=(TTG.ToontownCentral, Anywhere)),
           FishProperties(weightMin=2, weightMax=8, rarity=6, zoneList=(TTG.ToontownCentral, TTG.MinniesMelodyland)),
          ),
      6: ( FishProperties(weightMin=8, weightMax=12, rarity=1, zoneList=(TTG.TheBrrrgh,)),
          ),
      8: ( FishProperties(weightMin=1, weightMax=5, rarity=1, zoneList=(Anywhere,)),
           FishProperties(weightMin=2, weightMax=6, rarity=2, zoneList=(TTG.MinniesMelodyland, Anywhere)),
           FishProperties(weightMin=5, weightMax=10, rarity=5, zoneList=(TTG.MinniesMelodyland, Anywhere)),
           FishProperties(weightMin=1, weightMax=5, rarity=7, zoneList=(TTG.MyEstate, Anywhere)),
           FishProperties(weightMin=1, weightMax=5, rarity=10, zoneList=(TTG.MyEstate, Anywhere)),
          ),
      10: ( FishProperties(weightMin=6, weightMax=10, rarity=9, zoneList=(TTG.MyEstate, Anywhere,)),
          ),
      12: ( FishProperties(weightMin=7, weightMax=15, rarity=1, zoneList=(TTG.DonaldsDock, Anywhere)),
            FishProperties(weightMin=18, weightMax=20, rarity=6, zoneList=(TTG.DonaldsDock, TTG.MyEstate)),
            FishProperties(weightMin=1, weightMax=5, rarity=5, zoneList=(TTG.DonaldsDock, TTG.MyEstate)),
            FishProperties(weightMin=3, weightMax=7, rarity=4, zoneList=(TTG.DonaldsDock, TTG.MyEstate)),
            FishProperties(weightMin=1, weightMax=2, rarity=2, zoneList=(TTG.DonaldsDock, Anywhere)),
          ),
      14: ( FishProperties(weightMin=2, weightMax=6, rarity=1, zoneList=(TTG.DaisyGardens, TTG.MyEstate, Anywhere)),
            FishProperties(weightMin=2, weightMax=6, rarity=3, zoneList=(TTG.DaisyGardens, TTG.MyEstate)),
          ),
      16: ( FishProperties(weightMin=4, weightMax=12, rarity=5, zoneList=(TTG.MinniesMelodyland, Anywhere)),
            FishProperties(weightMin=4, weightMax=12, rarity=7, zoneList=(TTG.BaritoneBoulevard, TTG.MinniesMelodyland)),
            FishProperties(weightMin=4, weightMax=12, rarity=8, zoneList=(TTG.TenorTerrace, TTG.MinniesMelodyland)),
          ),
      18: ( FishProperties(weightMin=2, weightMax=4, rarity=3, zoneList=(TTG.DonaldsDock, Anywhere)),
            FishProperties(weightMin=5, weightMax=8, rarity=7, zoneList=(TTG.TheBrrrgh,)),
            FishProperties(weightMin=4, weightMax=6, rarity=8, zoneList=(TTG.LighthouseLane,)),
          ),
      20: ( FishProperties(weightMin=4, weightMax=6, rarity=1, zoneList=(TTG.DonaldsDreamland,)),
            FishProperties(weightMin=14, weightMax=18, rarity=10, zoneList=(TTG.DonaldsDreamland,)),
            FishProperties(weightMin=6, weightMax=10, rarity=8, zoneList=(TTG.LullabyLane,)),
            FishProperties(weightMin=1, weightMax=1, rarity=3, zoneList=(TTG.DonaldsDreamland,)),
            FishProperties(weightMin=2, weightMax=6, rarity=6, zoneList=(TTG.LullabyLane,)),
            FishProperties(weightMin=10, weightMax=14, rarity=4, zoneList=(TTG.DonaldsDreamland, TTG.DaisyGardens)),
          ),
      22: ( FishProperties(weightMin=12, weightMax=16, rarity=2, zoneList=(TTG.MyEstate, TTG.DaisyGardens, Anywhere)),
            FishProperties(weightMin=14, weightMax=18, rarity=3, zoneList=(TTG.MyEstate, TTG.DaisyGardens, Anywhere)),
            FishProperties(weightMin=14, weightMax=20, rarity=5, zoneList=(TTG.MyEstate, TTG.DaisyGardens)),
            FishProperties(weightMin=14, weightMax=20, rarity=7, zoneList=(TTG.MyEstate, TTG.DaisyGardens)),
          ),
      24: ( FishProperties(weightMin=9, weightMax=11, rarity=3, zoneList=(Anywhere,)),
            FishProperties(weightMin=8, weightMax=12, rarity=5, zoneList=(TTG.DaisyGardens, TTG.DonaldsDock)),
            FishProperties(weightMin=8, weightMax=12, rarity=6, zoneList=(TTG.DaisyGardens, TTG.DonaldsDock)),
            FishProperties(weightMin=8, weightMax=16, rarity=7, zoneList=(TTG.DaisyGardens, TTG.DonaldsDock)),
          ),
      26: ( FishProperties(weightMin=10, weightMax=18, rarity=2, zoneList=(TTG.TheBrrrgh,)),
            FishProperties(weightMin=10, weightMax=18, rarity=3, zoneList=(TTG.TheBrrrgh,)),
            FishProperties(weightMin=10, weightMax=18, rarity=4, zoneList=(TTG.TheBrrrgh,)),
            FishProperties(weightMin=10, weightMax=18, rarity=5, zoneList=(TTG.TheBrrrgh,)),
            FishProperties(weightMin=12, weightMax=20, rarity=6, zoneList=(TTG.TheBrrrgh,)),
            FishProperties(weightMin=14, weightMax=20, rarity=7, zoneList=(TTG.TheBrrrgh,)),
            FishProperties(weightMin=14, weightMax=20, rarity=8, zoneList=(TTG.SleetStreet, TTG.TheBrrrgh)),
            FishProperties(weightMin=16, weightMax=20, rarity=10, zoneList=(TTG.WalrusWay, TTG.TheBrrrgh)),
          ),
      28: ( FishProperties(weightMin=2, weightMax=10, rarity=2, zoneList=(TTG.DonaldsDock, Anywhere)),
            FishProperties(weightMin=4, weightMax=10, rarity=6, zoneList=(TTG.BarnacleBoulevard, TTG.DonaldsDock)),
            FishProperties(weightMin=4, weightMax=10, rarity=7, zoneList=(TTG.SeaweedStreet, TTG.DonaldsDock)),
          ),
      30: ( FishProperties(weightMin=13, weightMax=17, rarity=5, zoneList=(TTG.MinniesMelodyland, Anywhere)),
            FishProperties(weightMin=16, weightMax=20, rarity=10, zoneList=(TTG.AltoAvenue, TTG.MinniesMelodyland)),
            FishProperties(weightMin=12, weightMax=18, rarity=9, zoneList=(TTG.TenorTerrace, TTG.MinniesMelodyland)),
            FishProperties(weightMin=12, weightMax=18, rarity=6, zoneList=(TTG.MinniesMelodyland,)),
            FishProperties(weightMin=12, weightMax=18, rarity=7, zoneList=(TTG.MinniesMelodyland,)),
          ),
      32: ( FishProperties(weightMin=1, weightMax=5, rarity=2, zoneList=(TTG.ToontownCentral, TTG.MyEstate, Anywhere)),
            FishProperties(weightMin=1, weightMax=5, rarity=3, zoneList=(TTG.TheBrrrgh, TTG.MyEstate, Anywhere)),
            FishProperties(weightMin=1, weightMax=5, rarity=4, zoneList=(TTG.DaisyGardens, TTG.MyEstate)),
            FishProperties(weightMin=1, weightMax=5, rarity=5, zoneList=(TTG.DonaldsDreamland, TTG.MyEstate)),
            FishProperties(weightMin=1, weightMax=5, rarity=10, zoneList=(TTG.TheBrrrgh, TTG.DonaldsDreamland)),
          ),
      34: ( FishProperties(weightMin=1, weightMax=20, rarity=10, zoneList=(TTG.DonaldsDreamland, Anywhere)),
          ),
    }
    emptyRodDict = {}
    for rodIndex in RodHandler.getRodDict():
        emptyRodDict[rodIndex] = {}
    anywhereDict = copy.deepcopy(emptyRodDict)
    pondInfoDict = {}

    for genus, speciesList in FISHES.items():
        for species in range(len(speciesList)):
            speciesDesc = speciesList[species]
            rarity = speciesDesc.rarity
            zoneList = speciesDesc.zoneList
            for zoneIndex in range(len(zoneList)):
                zone = zoneList[zoneIndex]
                effectiveRarity = RarityHandler.getEffectiveRarity(rarity, MAX_RARITY, zoneIndex)
                if zone == Anywhere:
                    for rodIndex, rarityDict in anywhereDict.items():
                        if WeightHandler.canBeCaughtByRod(FISHES, RodHandler.getRodDict(), genus, species, rodIndex):
                            fishList = rarityDict.setdefault(effectiveRarity, [])
                            fishList.append( (genus, species) )
                else:
                    pondZones = [zone]
                    subZones = ToontownGlobals.HoodHierarchy.get(zone)
                    if subZones:
                        pondZones.extend(subZones)
                    for pondZone in pondZones:
                        if pondZone in pondInfoDict:
                            pondRodDict = pondInfoDict[pondZone]
                        else:
                            pondRodDict = copy.deepcopy(emptyRodDict)
                            pondInfoDict[pondZone] = pondRodDict
                        for rodIndex, rarityDict in pondRodDict.items():
                            if WeightHandler.canBeCaughtByRod(FISHES, RodHandler.getRodDict(), genus, species, rodIndex):
                                fishList = rarityDict.setdefault(effectiveRarity, [])
                                fishList.append( (genus, species) )
    for zone, _rodDict in pondInfoDict.items():
        for rodIndex, anywhereRarityDict in anywhereDict.items():
            for rarity, anywhereFishList in anywhereRarityDict.items():
                rarityDict = pondRodDict[rodIndex]
                fishList = rarityDict.setdefault(rarity, [])
                fishList.extend(anywhereFishList)

    def getRandomWeight(genus, species, rodIndex):
        minFishWeight, maxFishWeight = WeightHandler.getWeightRange(FishGlobals.FISHES, genus, species)
        if rodIndex == None:
            minWeight = minFishWeight
            maxWeight = maxFishWeight
        else:
            minWeight, maxWeight = WeightHandler.getRodWeightRange(RodHandler.getRodDict(), rodIndex)
            if minFishWeight > minWeight:
                minWeight = minFishWeight
            if maxFishWeight < maxWeight:
                maxWeight = maxFishWeight

        randNumA = random.random()
        randNumB = random.random()

        randNum = (randNumA + randNumB) / 2.0
        randWeight = minWeight + ((maxWeight - minWeight) * randNum)

        return int(round(randWeight * 16))

    def rollRarityDice(rodId):
        diceRoll = random.random()

        exp = RodHandler.getRarity(rodId)
        rarity = int(math.ceil(10 * (1 - math.pow(diceRoll, exp))))

        if rarity <= 0:
            rarity = 1

        return rarity

    def getRandomFishVitals(zoneId, rodId):
        rarity = FishGlobals.rollRarityDice(rodId)
        rodDict = FishGlobals.pondInfoDict.get(zoneId)
        rarityDict = rodDict.get(rodId)
        fishList = rarityDict.get(rarity)
        if fishList:
            genus, species = random.choice(fishList)
            weight = FishGlobals.getRandomWeight(genus, species, rodId)
            return (1, genus, species, weight)
        return (0, 0, 0, 0)

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
        print(power, heading)
        senderId = self.air.currentAvatarSender
        if self.avId != senderId:
            return
        if power < 0 or power > 1:
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
        castCost = RodHandler.getCastCost(sender.getFishingRod())

        if money < castCost:
            self.normalExit()
            return

        sender.b_setMoney(money - castCost)
        self.d_setMovie(FishMovies.CastMovie, power=power, h=heading)
        self.__startTimeout(self.TIMEOUT)

    def hitTarget(self, code, item):
        if code == FishItems.QuestItem:
            self.d_setMovie(FishMovies.PullInMovie, code=code, itemDesc1=item)
        elif code in (FishItems.FishItem,
                      FishItems.FishItemNewEntry,
                      FishItems.FishItemNewRecord):
            genus, species, weight = item.getVitals()
            self.d_setMovie(FishMovies.PullInMovie, code=code, itemDesc1=genus,
                            itemDesc2=species, itemDesc3=weight)
        elif code == FishItems.JellybeanItem:
            self.d_setMovie(FishMovies.PullInMovie, code=code, itemDesc1=item)
        else:
            self.d_setMovie(FishMovies.PullInMovie, code=code)
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
        rodId = av.getFishingRod()

        # TODO: prioritize quest items
        randNum = random.randint(0, 100)
        for item, chance in FishItems.item2Chance.items():
            if randNum <= chance:
                itemType = item
                break

        if itemType == FishItems.FishItem:
            success, genus, species, weight = FishGlobals.getRandomFishVitals(self.getArea(), rodId)
            if success:
                fish = FishBase(genus, species, weight)
                inTank, hasBiggerAlready = av.fishTank.hasFish(genus, species, weight)
                added = av.addFishToTank(fish)
                if added:
                    collectResult = av.fishCollection.getCollectResult(fish)
                    if collectResult == COLLECT_NO_UPDATE:
                        return (itemType, fish)
                    elif collectResult == COLLECT_NEW_ENTRY:
                        if not inTank:
                            return (FishItems.FishItemNewEntry, fish)
                        elif not hasBiggerAlready:
                            return (FishItems.FishItemNewRecord, fish)
                        return (itemType, fish)
                    elif collectResult == COLLECT_NEW_RECORD:
                        if hasBiggerAlready:
                            return (itemType, fish)
                        return (FishItems.FishItemNewRecord, fish)
                else:
                    return (FishItems.OverTankLimit, None)
            else:
                return (FishItems.BootItem, None)
        elif itemType == FishItems.BootItem:
            return (FishItems.BootItem, None)
        elif itemType == FishItems.JellybeanItem:
            value = RodHandler.getJellybeanReward(rodId)
            av.addMoney(value)
            return(itemType, value)

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