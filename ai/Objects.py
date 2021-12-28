import time
import math
import copy
import random
import string

from datetime import datetime

from .DistributedObjectAI import DistributedObjectAI
from ai.toon.DistributedToonAI import DistributedToonAI
from ai.toon.DistributedToonAI import DistributedPlayerAI
from ai.globals import HoodGlobals as HG
from ai.ToontownGlobals import MaxHpLimit
from typing import List, Optional, Dict, NamedTuple
from dataslots import with_slots
from dataclasses import dataclass

from panda3d.core import Datagram
from otp.util import getPuppetChannel, addServerHeader
from otp.messagetypes import CLIENT_FRIEND_ONLINE

from ai.catalog import CatalogItem
from ai.catalog.CatalogBeanItem import CatalogBeanItem
from ai.catalog.CatalogClothingItem import CatalogClothingItem
from ai import ToontownGlobals

class DistributedDistrictAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.name = ''
        self.available = False

    def d_setName(self, name):
        self.sendUpdate('setName', [name])

    def b_setName(self, name):
        self.name = name
        self.d_setName(name)

    def getName(self):
        return self.name

    def d_setAvailable(self, available):
        self.sendUpdate('setAvailable', [available])

    def b_setAvailable(self, available):
        self.available = available
        self.d_setAvailable(available)

    def getAvailable(self):
        return self.available

class ToontownDistrictAI(DistributedDistrictAI):
    def __init__(self, air):
        DistributedDistrictAI.__init__(self, air)
        self.ahnnLog = False

    def allowAHNNLog(self, ahnnLog):
        self.ahnnLog = ahnnLog

    def d_allowAHNNLog(self, ahnnLog):
        self.sendUpdate('allowAHNNLog', [ahnnLog])

    def b_allowAHNNLog(self, ahnnLog):
        self.allowAHNNLog(ahnnLog)
        self.d_allowAHNNLog(ahnnLog)

    def getAllowAHNNLog(self):
        return self.ahnnLog

    def handleChildArrive(self, obj, zoneId):
        if isinstance(obj, DistributedToonAI):
            obj.sendUpdate('arrivedOnDistrict', [self.doId])
            self.air.incrementPopulation()

class ToontownDistrictStatsAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.toontownDistrictId = 0
        self.avatarCount = 0
        self.newAvatarCount = 0

    def settoontownDistrictId(self, toontownDistrictId):
        self.toontownDistrictId = toontownDistrictId

    def d_settoontownDistrictId(self, toontownDistrictId):
        self.sendUpdate('settoontownDistrictId', [toontownDistrictId])

    def b_settoontownDistrictId(self, toontownDistrictId):
        self.settoontownDistrictId(toontownDistrictId)
        self.d_settoontownDistrictId(toontownDistrictId)

    def gettoontownDistrictId(self):
        return self.toontownDistrictId

    def setAvatarCount(self, avatarCount):
        self.avatarCount = avatarCount

    def d_setAvatarCount(self, avatarCount):
        self.sendUpdate('setAvatarCount', [avatarCount])

    def b_setAvatarCount(self, avatarCount):
        self.setAvatarCount(avatarCount)
        self.d_setAvatarCount(avatarCount)

    def getAvatarCount(self):
        return self.avatarCount

    def setNewAvatarCount(self, newAvatarCount):
        self.newAvatarCount = newAvatarCount

    def d_setNewAvatarCount(self, newAvatarCount):
        self.sendUpdate('setNewAvatarCount', [newAvatarCount])

    def b_setNewAvatarCount(self, newAvatarCount):
        self.setNewAvatarCount(newAvatarCount)
        self.d_setNewAvatarCount(newAvatarCount)

    def getNewAvatarCount(self):
        return self.newAvatarCount

class DistributedInGameNewsMgrAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.latestIssue = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(1379606399))

    def getLatestIssueStr(self):
        return self.latestIssue

@with_slots
@dataclass
class WeeklyHoliday:
    holidayId: int
    weekday: int

    def __iter__(self):
        yield self.holidayId
        yield self.weekday

@with_slots
@dataclass
class YearlyHoliday:
    holidayId: int
    startMonth: int
    startDay: int
    endMonth: int
    endDay: int

    def __iter__(self):
        yield self.holidayId
        yield (self.startMonth, self.startDay)
        yield (self.endMonth, self.endDay)

@with_slots
@dataclass
class OncelyHoliday:
    holidayId: int
    startMonth: int
    startDay: int
    endMonth: int
    endDay: int

    def __iter__(self):
        yield self.holidayId
        yield (self.startMonth, self.startDay)
        yield (self.endMonth, self.endDay)

@with_slots
@dataclass
class MultipleStartDate:
    startYear: int
    startMonth: int
    startDay: int
    endYear: int
    endMonth: int
    endDay: int

    def __iter__(self):
        yield (self.startYear, self.startMonth, self.startDay)
        yield (self.endYear, self.endMonth, self.endDay)

class MultipleStartHoliday:
    __slots__ = 'holidayId', 'times'

    def __init__(self, holidayId: int, times: List[MultipleStartDate]):
        self.holidayId = holidayId
        self.times = [tuple(date) for date in times]

    def __iter__(self):
        yield self.holidayId
        yield self.times

from ai.HolidayGlobals import *

class NewsManagerAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.weeklyHolidays: List[WeeklyHoliday] = []
        self.yearlyHolidays: List[YearlyHoliday] = []
        self.oncelyHolidays: List[OncelyHoliday] = []
        self.multipleStartHolidays: List[MultipleStartHoliday] = []
        self.relativeHolidays = []
        self.holidayIds: List[int] = []

        self.holidays = [
            SillyMeterHolidayAI(self.air)
        ]

    def announceGenerate(self):
        for holiday in self.holidays:
            holiday.start()

    def getWeeklyCalendarHolidays(self):
        return [tuple(holiday) for holiday in self.weeklyHolidays]

    def getYearlyCalendarHolidays(self):
        return [tuple(holiday) for holiday in self.yearlyHolidays]

    def getOncelyCalendarHolidays(self):
        return [tuple(holiday) for holiday in self.oncelyHolidays]

    def getMultipleStartHolidays(self):
        return [tuple(holiday) for holiday in self.multipleStartHolidays]

    # TODO: figure out how relative holidays work
    def getRelativelyCalendarHolidays(self):
        return []

    def d_setHolidayIdList(self):
        self.sendUpdate('setHolidayIdList', [self.holidayIds])

    def d_sendSystemMessage(self, msg: str, msgType = 0):
        self.sendUpdate('sendSystemMessage', [msg, msgType])

    def forceHolidayStart(self, holidayId: int):
        self.holidayIds.append(holidayId)
        self.d_setHolidayIdList()

class HolidayBaseAI:
    holidayId = None

    def __init__(self, air):
        self.air = air

    def start(self):
        self.air.newsManager.holidayIds.append(self.holidayId)
        self.air.newsManager.d_setHolidayIdList()

    def stop(self):
        self.air.newsManager.holidayIds.remove(self.holidayId)
        self.air.newsManager.d_setHolidayIdList()

from otp.constants import *

class DistributedPhaseEventMgrAI(DistributedObjectAI):
    def getNumPhases(self):
        raise NotImplementedError

    def getDates(self):
        raise NotImplementedError

    def getCurPhase(self):
        raise NotImplementedError

    def getIsRunning(self):
        return False

class DistributedSillyMeterMgrAI(DistributedPhaseEventMgrAI):
    def getNumPhases(self):
        return 15

    def getDates(self):
        return []

    def getCurPhase(self):
        return 11

    def getIsRunning(self):
        return 1

class SillyMeterHolidayAI(HolidayBaseAI):
    holidayId = SILLYMETER_HOLIDAY

    def start(self):
        super().start()
        self.air.sillyMgr = DistributedSillyMeterMgrAI(self.air)
        self.air.sillyMgr.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

    def stop(self):
        super().stop()
        self.air.sillyMgr.requestDelete()
        del self.air.sillyMgr

from .DistributedObjectGlobalAI import DistributedObjectGlobalAI

class FriendRequest:
    CANCELLED = -1
    INACTIVE = 0
    FRIEND_QUERY = 1
    FRIEND_CONSIDERING = 2

    def __init__(self, avId, requestedId, state):
        self.avId = avId
        self.requestedId = requestedId
        self.state = state

    @property
    def cancelled(self):
        return self.state == FriendRequest.CANCELLED

    def isRequestedId(self, avId):
        return avId == self.requestedId

class InviteeResponse:
    NOT_AVAILABLE = 0
    ASKING = 1
    ALREADY_FRIENDS = 2
    SELF_FRIEND = 3
    IGNORED = 4
    NO_NEW_FRIENDS = 6
    NO = 10
    TOO_MANY_FRIENDS = 13

MAX_FRIENDS = 50
MAX_PLAYER_FRIENDS = 300

class FriendManagerAI(DistributedObjectGlobalAI):
    doId = OTP_DO_ID_FRIEND_MANAGER

    def __init__(self, air):
        DistributedObjectGlobalAI.__init__(self, air)
        self.requests: Dict[int, FriendRequest] = {}
        self._context = 0

    @property
    def next_context(self):
        self._context = (self._context + 1) & 0xFFFFFFFF
        return self._context

    def friendQuery(self, requested):
        avId = self.air.currentAvatarSender
        if requested not in self.air.doTable:
            return
        av = self.air.doTable.get(avId)
        if not av:
            return
        context = self.next_context
        self.requests[context] = FriendRequest(avId, requested, FriendRequest.FRIEND_QUERY)
        self.sendUpdateToAvatar(requested, 'inviteeFriendQuery', [avId, av.getName(), av.getDNAString(), context])

    def cancelFriendQuery(self, context):
        avId = self.air.currentAvatarSender
        if avId not in self.air.doTable:
            return

        request = self.requests.get(context)
        if not request or avId != request.avId:
            return
        request.state = FriendRequest.CANCELLED
        self.sendUpdateToAvatar(request.requestedId, 'inviteeCancelFriendQuery', [context])

    def inviteeFriendConsidering(self, response, context):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)
        if not av:
            return

        request = self.requests.get(context)
        if not request:
            return

        if not request.isRequestedId(avId):
            return

        if request.state != FriendRequest.FRIEND_QUERY:
            return

        if response != InviteeResponse.ASKING:
            request.state = FriendRequest.CANCELLED
            del self.requests[context]
        else:
            request.state = FriendRequest.FRIEND_CONSIDERING

        self.sendUpdateToAvatar(request.avId, 'friendConsidering', [response, context])

    def inviteeFriendResponse(self, response, context):
        avId = self.air.currentAvatarSender
        requested = self.air.doTable.get(avId)
        if not requested:
            return

        request = self.requests.get(context)
        if not request:
            return

        if not request.isRequestedId(avId):
            return

        if request.state != FriendRequest.FRIEND_CONSIDERING:
            return

        self.sendUpdateToAvatar(request.avId, 'friendResponse', [response, context])

        if response == 1:
            requester = self.air.doTable.get(request.avId)

            if not (requested and requester):
                # Likely they logged off just before a response was sent. RIP.
                return

            requested.extendFriendsList(requester.doId, False)
            requester.extendFriendsList(requested.doId, False)

            requested.d_setFriendsList(requested.getFriendsList())
            requester.d_setFriendsList(requester.getFriendsList())

            taskMgr.doMethodLater(1, self.sendFriendOnline, f'send-online-{requested.doId}-{requester.doId}',
                                  extraArgs=[requested.doId, requester.doId])
            taskMgr.doMethodLater(1, self.sendFriendOnline, f'send-online-{requester.doId}-{requested.doId}',
                                  extraArgs=[requester.doId, requested.doId])

    def requestSecret(self):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)

        if len(av.getFriendsList()) >= MAX_FRIENDS:
            self.d_requestSecretResponse(0, '')
        else:
            first = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(3))
            second = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(3))

            code = f'{first.lower()} {second.lower()}'
            self.d_requestSecretResponse(avId, 1, code)

    def d_requestSecretResponse(self, avId, result, secret):
        if not avId:
            return

        self.sendUpdateToAvatar(avId, 'requestSecretResponse', [result, secret])

    def sendFriendOnline(self, avId, otherAvId):
        # Need this delay so that `setFriendsList` is set first to avoid
        # the online whisper message.
        dg = Datagram()
        addServerHeader([getPuppetChannel(avId)], self.air.ourChannel, CLIENT_FRIEND_ONLINE)
        dg.addUint32(otherAvId)
        self.air.send(dg)

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

class FishManager:
    ANYWHERE = 1
    GLOBAL_RARITY_DIAL_BASE = 4.3
    MAX_RARITY = 10
    OVERALL_VALUE_SCALE = 15
    RARITY_VALUE_SCALE = 0.2
    WEIGHT_VALUE_SCALE = 0.05 / 16.0
    FISH_PER_BONUS = 10
    totalFish = 0

    def __init__(self):
        self.rodDict = {
          0: FishingRod(weightMin=0, weightMax=4, rarity=(1.0 / (self.GLOBAL_RARITY_DIAL_BASE * 1)),
                        castCost=1, jellybeanReward=10),
          1: FishingRod(weightMin=0, weightMax=8, rarity=(1.0 / (self.GLOBAL_RARITY_DIAL_BASE * 1)),
                        castCost=2, jellybeanReward=20),
          2: FishingRod(weightMin=0, weightMax=12, rarity=(1.0 / (self.GLOBAL_RARITY_DIAL_BASE * 1)),
                        castCost=3, jellybeanReward=30),
          3: FishingRod(weightMin=0, weightMax=16, rarity=(1.0 / (self.GLOBAL_RARITY_DIAL_BASE * 1)),
                        castCost=4, jellybeanReward=75),
          4: FishingRod(weightMin=0, weightMax=20, rarity=(1.0 / (self.GLOBAL_RARITY_DIAL_BASE * 1)),
                        castCost=5, jellybeanReward=150),
        }
        self.fishes = {
          0: ( FishProperties(weightMin=1, weightMax=3, rarity=1, zoneList=(self.ANYWHERE,)),
               FishProperties(weightMin=1, weightMax=1, rarity=4, zoneList=(HG.ToontownCentral, self.ANYWHERE)),
               FishProperties(weightMin=3, weightMax=5, rarity=5, zoneList=(HG.PunchlinePlace, HG.TheBrrrgh)),
               FishProperties(weightMin=3, weightMax=5, rarity=3, zoneList=(HG.SillyStreet, HG.DaisyGardens)),
               FishProperties(weightMin=1, weightMax=5, rarity=2, zoneList=(HG.LoopyLane, HG.ToontownCentral)),
              ),
          2: ( FishProperties(weightMin=2, weightMax=6, rarity=1, zoneList=(HG.DaisyGardens, self.ANYWHERE)),
               FishProperties(weightMin=2, weightMax=6, rarity=9, zoneList=(HG.ElmStreet, HG.DaisyGardens)),
               FishProperties(weightMin=5, weightMax=11, rarity=4, zoneList=(HG.LullabyLane,)),
               FishProperties(weightMin=2, weightMax=6, rarity=3, zoneList=(HG.DaisyGardens, HG.MyEstate)),
               FishProperties(weightMin=5, weightMax=11, rarity=2, zoneList=(HG.DonaldsDreamland, HG.MyEstate)),
              ),
          4: ( FishProperties(weightMin=2, weightMax=8, rarity=1, zoneList=(HG.ToontownCentral, self.ANYWHERE,)),
               FishProperties(weightMin=2, weightMax=8, rarity=4, zoneList=(HG.ToontownCentral, self.ANYWHERE)),
               FishProperties(weightMin=2, weightMax=8, rarity=2, zoneList=(HG.ToontownCentral, self.ANYWHERE)),
               FishProperties(weightMin=2, weightMax=8, rarity=6, zoneList=(HG.ToontownCentral, HG.MinniesMelodyland)),
              ),
          6: ( FishProperties(weightMin=8, weightMax=12, rarity=1, zoneList=(HG.TheBrrrgh,)),
              ),
          8: ( FishProperties(weightMin=1, weightMax=5, rarity=1, zoneList=(self.ANYWHERE,)),
               FishProperties(weightMin=2, weightMax=6, rarity=2, zoneList=(HG.MinniesMelodyland, self.ANYWHERE)),
               FishProperties(weightMin=5, weightMax=10, rarity=5, zoneList=(HG.MinniesMelodyland, self.ANYWHERE)),
               FishProperties(weightMin=1, weightMax=5, rarity=7, zoneList=(HG.MyEstate, self.ANYWHERE)),
               FishProperties(weightMin=1, weightMax=5, rarity=10, zoneList=(HG.MyEstate, self.ANYWHERE)),
              ),
          10: ( FishProperties(weightMin=6, weightMax=10, rarity=9, zoneList=(HG.MyEstate, self.ANYWHERE,)),
              ),
          12: ( FishProperties(weightMin=7, weightMax=15, rarity=1, zoneList=(HG.DonaldsDock, self.ANYWHERE)),
                FishProperties(weightMin=18, weightMax=20, rarity=6, zoneList=(HG.DonaldsDock, HG.MyEstate)),
                FishProperties(weightMin=1, weightMax=5, rarity=5, zoneList=(HG.DonaldsDock, HG.MyEstate)),
                FishProperties(weightMin=3, weightMax=7, rarity=4, zoneList=(HG.DonaldsDock, HG.MyEstate)),
                FishProperties(weightMin=1, weightMax=2, rarity=2, zoneList=(HG.DonaldsDock, self.ANYWHERE)),
              ),
          14: ( FishProperties(weightMin=2, weightMax=6, rarity=1, zoneList=(HG.DaisyGardens, HG.MyEstate, self.ANYWHERE)),
                FishProperties(weightMin=2, weightMax=6, rarity=3, zoneList=(HG.DaisyGardens, HG.MyEstate)),
              ),
          16: ( FishProperties(weightMin=4, weightMax=12, rarity=5, zoneList=(HG.MinniesMelodyland, self.ANYWHERE)),
                FishProperties(weightMin=4, weightMax=12, rarity=7, zoneList=(HG.BaritoneBoulevard, HG.MinniesMelodyland)),
                FishProperties(weightMin=4, weightMax=12, rarity=8, zoneList=(HG.TenorTerrace, HG.MinniesMelodyland)),
              ),
          18: ( FishProperties(weightMin=2, weightMax=4, rarity=3, zoneList=(HG.DonaldsDock, self.ANYWHERE)),
                FishProperties(weightMin=5, weightMax=8, rarity=7, zoneList=(HG.TheBrrrgh,)),
                FishProperties(weightMin=4, weightMax=6, rarity=8, zoneList=(HG.LighthouseLane,)),
              ),
          20: ( FishProperties(weightMin=4, weightMax=6, rarity=1, zoneList=(HG.DonaldsDreamland,)),
                FishProperties(weightMin=14, weightMax=18, rarity=10, zoneList=(HG.DonaldsDreamland,)),
                FishProperties(weightMin=6, weightMax=10, rarity=8, zoneList=(HG.LullabyLane,)),
                FishProperties(weightMin=1, weightMax=1, rarity=3, zoneList=(HG.DonaldsDreamland,)),
                FishProperties(weightMin=2, weightMax=6, rarity=6, zoneList=(HG.LullabyLane,)),
                FishProperties(weightMin=10, weightMax=14, rarity=4, zoneList=(HG.DonaldsDreamland, HG.DaisyGardens)),
              ),
          22: ( FishProperties(weightMin=12, weightMax=16, rarity=2, zoneList=(HG.MyEstate, HG.DaisyGardens, self.ANYWHERE)),
                FishProperties(weightMin=14, weightMax=18, rarity=3, zoneList=(HG.MyEstate, HG.DaisyGardens, self.ANYWHERE)),
                FishProperties(weightMin=14, weightMax=20, rarity=5, zoneList=(HG.MyEstate, HG.DaisyGardens)),
                FishProperties(weightMin=14, weightMax=20, rarity=7, zoneList=(HG.MyEstate, HG.DaisyGardens)),
              ),
          24: ( FishProperties(weightMin=9, weightMax=11, rarity=3, zoneList=(self.ANYWHERE,)),
                FishProperties(weightMin=8, weightMax=12, rarity=5, zoneList=(HG.DaisyGardens, HG.DonaldsDock)),
                FishProperties(weightMin=8, weightMax=12, rarity=6, zoneList=(HG.DaisyGardens, HG.DonaldsDock)),
                FishProperties(weightMin=8, weightMax=16, rarity=7, zoneList=(HG.DaisyGardens, HG.DonaldsDock)),
              ),
          26: ( FishProperties(weightMin=10, weightMax=18, rarity=2, zoneList=(HG.TheBrrrgh,)),
                FishProperties(weightMin=10, weightMax=18, rarity=3, zoneList=(HG.TheBrrrgh,)),
                FishProperties(weightMin=10, weightMax=18, rarity=4, zoneList=(HG.TheBrrrgh,)),
                FishProperties(weightMin=10, weightMax=18, rarity=5, zoneList=(HG.TheBrrrgh,)),
                FishProperties(weightMin=12, weightMax=20, rarity=6, zoneList=(HG.TheBrrrgh,)),
                FishProperties(weightMin=14, weightMax=20, rarity=7, zoneList=(HG.TheBrrrgh,)),
                FishProperties(weightMin=14, weightMax=20, rarity=8, zoneList=(HG.SleetStreet, HG.TheBrrrgh)),
                FishProperties(weightMin=16, weightMax=20, rarity=10, zoneList=(HG.WalrusWay, HG.TheBrrrgh)),
              ),
          28: ( FishProperties(weightMin=2, weightMax=10, rarity=2, zoneList=(HG.DonaldsDock, self.ANYWHERE)),
                FishProperties(weightMin=4, weightMax=10, rarity=6, zoneList=(HG.BarnacleBoulevard, HG.DonaldsDock)),
                FishProperties(weightMin=4, weightMax=10, rarity=7, zoneList=(HG.SeaweedStreet, HG.DonaldsDock)),
              ),
          30: ( FishProperties(weightMin=13, weightMax=17, rarity=5, zoneList=(HG.MinniesMelodyland, self.ANYWHERE)),
                FishProperties(weightMin=16, weightMax=20, rarity=10, zoneList=(HG.AltoAvenue, HG.MinniesMelodyland)),
                FishProperties(weightMin=12, weightMax=18, rarity=9, zoneList=(HG.TenorTerrace, HG.MinniesMelodyland)),
                FishProperties(weightMin=12, weightMax=18, rarity=6, zoneList=(HG.MinniesMelodyland,)),
                FishProperties(weightMin=12, weightMax=18, rarity=7, zoneList=(HG.MinniesMelodyland,)),
              ),
          32: ( FishProperties(weightMin=1, weightMax=5, rarity=2, zoneList=(HG.ToontownCentral, HG.MyEstate, self.ANYWHERE)),
                FishProperties(weightMin=1, weightMax=5, rarity=3, zoneList=(HG.TheBrrrgh, HG.MyEstate, self.ANYWHERE)),
                FishProperties(weightMin=1, weightMax=5, rarity=4, zoneList=(HG.DaisyGardens, HG.MyEstate)),
                FishProperties(weightMin=1, weightMax=5, rarity=5, zoneList=(HG.DonaldsDreamland, HG.MyEstate)),
                FishProperties(weightMin=1, weightMax=5, rarity=10, zoneList=(HG.TheBrrrgh, HG.DonaldsDreamland)),
              ),
          34: ( FishProperties(weightMin=1, weightMax=20, rarity=10, zoneList=(HG.DonaldsDreamland, self.ANYWHERE)),
              ),
        }
        self.emptyRodDict = {}
        for rodIndex in self.getRodDict():
            self.emptyRodDict[rodIndex] = {}
        self.anywhereDict = copy.deepcopy(self.emptyRodDict)
        self.pondInfoDict = {}
        for genus, speciesList in self.getFishes().items():
            for species in range(len(speciesList)):
                self.totalFish += 1
                speciesDesc = speciesList[species]
                rarity = speciesDesc.rarity
                zoneList = speciesDesc.zoneList
                for zoneIndex in range(len(zoneList)):
                    zone = zoneList[zoneIndex]
                    effectiveRarity = self.getEffectiveRarity(rarity, zoneIndex)
                    if zone == self.ANYWHERE:
                        for rodIndex, rarityDict in self.anywhereDict.items():
                            if self.canBeCaughtByRod(genus, species, rodIndex):
                                fishList = rarityDict.setdefault(effectiveRarity, [])
                                fishList.append( (genus, species) )
                    else:
                        pondZones = [zone]
                        subZones = HG.HoodHierarchy.get(zone)
                        if subZones:
                            pondZones.extend(subZones)
                        for pondZone in pondZones:
                            if pondZone in self.pondInfoDict:
                                pondRodDict = self.pondInfoDict[pondZone]
                            else:
                                pondRodDict = copy.deepcopy(self.emptyRodDict)
                                self.pondInfoDict[pondZone] = pondRodDict
                            for rodIndex, rarityDict in pondRodDict.items():
                                if self.canBeCaughtByRod(genus, species, rodIndex):
                                    fishList = rarityDict.setdefault(effectiveRarity, [])
                                    fishList.append( (genus, species) )
        for zone, _rodDict in self.pondInfoDict.items():
            for rodIndex, self.anywhereRarityDict in self.anywhereDict.items():
                for rarity, anywhereFishList in self.anywhereRarityDict.items():
                    rarityDict = pondRodDict[rodIndex]
                    fishList = rarityDict.setdefault(rarity, [])
                    fishList.extend(anywhereFishList)

    def getFishes(self):
        return self.fishes

    def getRodDict(self):
        return self.rodDict

    def getWeightRange(self, genus, species):
        fishInfo = self.getFishes()[genus][species]
        return (fishInfo.weightMin, fishInfo.weightMax)

    def getRodWeightRange(self, rodIndex):
        rodProps = self.getRodDict()[rodIndex]
        return (rodProps.weightMin, rodProps.weightMax)

    def getRodRarity(self, rodId):
        return self.getRodDict()[rodId].rarity

    def getCastCost(self, rodId):
        return self.getRodDict()[rodId].castCost

    def getRodJellybeanReward(self, rodId):
        return self.getRodDict()[rodId].jellybeanReward

    def canBeCaughtByRod(self, genus, species, rodIndex):
        minFishWeight, maxFishWeight = self.getWeightRange(genus, species)
        minRodWeight, maxRodWeight = self.getRodWeightRange(rodIndex)
        if ((minRodWeight <= maxFishWeight) and
            (maxRodWeight >= minFishWeight)):
            return 1
        return 0

    def getEffectiveRarity(self, rarity, offset):
        if rarity + (offset) > self.MAX_RARITY:
            return self.MAX_RARITY
        return rarity + (offset)

    def getFishValue(self, genus, species, weight):
        rarity = self.getFishes()[genus][species].rarity
        rarityValue = math.pow(self.RARITY_VALUE_SCALE * rarity, 1.5)
        weightValue = math.pow(self.WEIGHT_VALUE_SCALE * weight, 1.1)
        value = self.OVERALL_VALUE_SCALE * (rarityValue + weightValue)
        finalValue = int(math.ceil(value))
        # TODO: holiday stuff
        return finalValue

    def getRandomWeight(self, genus, species, rodIndex):
        minFishWeight, maxFishWeight = self.getWeightRange(genus, species)
        if rodIndex == None:
            minWeight = minFishWeight
            maxWeight = maxFishWeight
        else:
            minWeight, maxWeight = self.getRodWeightRange(rodIndex)
            if minFishWeight > minWeight:
                minWeight = minFishWeight
            if maxFishWeight < maxWeight:
                maxWeight = maxFishWeight

        randNumA = random.random()
        randNumB = random.random()

        randNum = (randNumA + randNumB) / 2.0
        randWeight = minWeight + ((maxWeight - minWeight) * randNum)

        return int(round(randWeight * 16))

    def rollRarityDice(self, rodId):
        diceRoll = random.random()

        exp = self.getRodRarity(rodId)
        rarity = int(math.ceil(10 * (1 - math.pow(diceRoll, exp))))

        if rarity <= 0:
            rarity = 1

        return rarity

    def getRandomFishVitals(self, zoneId, rodId):
        rarity = self.rollRarityDice(rodId)
        rodDict = self.pondInfoDict.get(zoneId)
        rarityDict = rodDict.get(rodId)
        fishList = rarityDict.get(rarity)
        if fishList:
            genus, species = random.choice(fishList)
            weight = self.getRandomWeight(genus, species, rodId)
            return (1, genus, species, weight)
        return (0, 0, 0, 0)

    def creditFishTank(self, av: DistributedToonAI) -> bool:
        oldBonus = int(len(av.fishCollection) / self.FISH_PER_BONUS)

        # Give the avatar jellybeans in exchange for his fish.
        value = av.fishTank.getTotalValue()
        av.addMoney(value)

        # Update the avatar collection for each fish.
        for fish in av.fishTank.fishList:
            av.fishCollection.collectFish(fish)

        # Clear out the fish tank.
        av.b_setFishTank([], [], [])

        # Update the collection in the database.
        av.d_setFishCollection(*av.fishCollection.getNetLists())

        newBonus = int(len(av.fishCollection) / self.FISH_PER_BONUS)

        if newBonus > oldBonus:
            oldMaxHp = av.getMaxHp()
            newMaxHp = min(MaxHpLimit, oldMaxHp + newBonus - oldBonus)
            av.b_setMaxHp(nwMaxHp)

            # Also, give them a full heal.
            av.toonUp(newMaxHp)

            # Update their trophy list.
            newTrophies = av.getFishingTrophies()
            trophyId = len(newTrophies)
            newTrophies.append(trophyId)
            av.b_setFishingTrophies(newTrophies)

            return True

        return False

class MagicWordManagerAI(DistributedObjectAI):
    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

class ToontownMagicWordManagerAI(MagicWordManagerAI):
    def __init__(self, air):
        MagicWordManagerAI.__init__(self, air)

    def checkArguments(self, avId: int, magicWord: str, function, args) -> bool:
        fArgs = function.__code__.co_argcount - 1
        argCount = len(args)

        if argCount > fArgs:
            response = 'Invalid argument count!'
            self.sendResponseMessage(avId, response)
            return False

        minArgs = fArgs - (len(function.__defaults__) if function.__defaults__ else 0) - 1

        if argCount < minArgs:
            response = f'{magicWord} requires at least {str(minArgs)} arguments but received {str(argCount)}!'
            self.sendResponseMessage(avId, response)
            return False

        return True

    def sendResponseMessage(self, avId: int, message: str):
        self.sendUpdateToAvatar(avId, 'setMagicWordResponse', [message])

    def sendSystemMessage(self, av, msg: str) -> str:
        if msg == '':
            return

        for doId, do in list(self.air.doTable.items()):
            if isinstance(do, DistributedPlayerAI):
                if str(doId)[0] != str(self.air.district.doId)[0]:
                    do.d_setSystemMessage(0, msg)

        return 'Broadcasted message to everyone on this shard.'

    def setName(self, av: DistributedToonAI, name: str) -> str:
        av.b_setName(name)

        return f'Changed name to {name}.'

    def healUp(self, av: DistributedToonAI) -> str:
        av.b_setHp(av.getMaxHp())

        return 'Healed avatar.'

    def jeffBezos(self, av: DistributedToonAI) -> str:
        av.b_setMoney(av.getMaxMoney())

        return 'You are now Jeff Bezos.'

    def startHoliday(self, holidayId: int) -> str:
        if holidayId in self.air.newsManager.holidayIds:
            return f'Holiday {holidayId} is already running!'

        self.air.newsManager.forceHolidayStart(holidayId)

        return f'Holiday {holidayId} has started!'

    def nextCatalog(self, av: DistributedToonAI) -> str:
        self.air.catalogManager.deliverCatalogFor(av)

        return 'Postmaster Pete: Your next catalog has been delivered!'

    def deliverCatalogItems(self, av: DistributedToonAI) -> str:
        for item in av.onOrder:
            item.deliveryDate = int(time.time() / 60)

        av.onOrder.markDirty()
        av.b_setDeliverySchedule(av.onOrder)

        return f'Delivered {len(av.onOrder)} item(s).'

    def setMagicWord(self, magicWord: str, avId: int, zoneId: int, signature: str):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)

        if not av:
            return

        # Chop off the prefix at the start as its not needed.
        magicWord = magicWord[1:]
        # Split the Magic Word.
        splitWord = magicWord.split(' ')
        # Grab the arguments.
        args = splitWord[1:]
        # Make the Magic Word case insensitive.
        magicWord = splitWord[0].lower()
        del splitWord

        # Log this attempt.
        print(f'{av.getName()} ({avId}) executed Magic Word: {magicWord}.')

        # Grab all of our string arguments.
        string = ' '.join(str(x) for x in args)

        clientWords = [
            'run',
            'walk',
            'fps',
            'sit',
            'sbm'
        ]

        if magicWord in clientWords or magicWord == '':
            # We can ignore this.
            return

        response = ''

        if magicWord in ('system', 'smsg'):
            response = self.sendSystemMessage(av, msg = string)
        elif magicWord == 'name':
            response = self.setName(av, name = string)
        elif magicWord == 'startholiday':
            if self.checkArguments(avId, magicWord, self.startHoliday, args):
                response = self.startHoliday(holidayId = int(args[0]))
        elif magicWord == 'heal':
            response = self.healUp(av)
        elif magicWord in ('rich', 'jeffbezos'):
            response = self.jeffBezos(av)
        elif magicWord == 'nextcatalog':
            response = self.nextCatalog(av)
        elif magicWord == 'deliveritems':
            response = self.deliverCatalogItems(av)
        else:
            response = f'{magicWord} is not a valid Magic Word.'
            print(f'Unknown Magic Word: {magicWord} from avId: {avId}.')

        # Send our response to the client.
        self.sendResponseMessage(avId, response)

class TTCodeRedemptionMgrAI(DistributedObjectAI):
    Success = 0
    InvalidCode = 1
    ExpiredCode = 2
    Ineligible = 3
    AwardError = 4
    TooManyFails = 5
    ServiceUnavailable = 6

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

    def redeemCode(self, context: int, code: str):
        avId = self.air.currentAvatarSender
        av = self.air.doTable.get(avId)

        if not av:
            return

        code = code.lower()

        items = self.air.mongoInterface.findCodeMatch(code)

        if items is None:
            status = self.InvalidCode
            self.d_redeemCodeResult(avId, context, status)
            return

        # If our year is greater than 1, then we must have a month and day too.
        if items['ExpirationYear']:
            try:
                expYear = items['ExpirationYear']
                expMonth = items['ExpirationMonth']
                expDay = items['ExpirationDay']
            except:
                print(f'Code {code} does not have a proper expiration date.')
                status = self.InvalidCode
                self.d_redeemCodeResult(avId, context, status)
                return

            # TODO: should this go off Toontown Time instead of local time?
            today = datetime.today()
            todayYear = today.year
            todayMonth = today.month
            todayDay = today.month

            datetimeCode = datetime(expYear, expMonth, expDay)
            datetimeToday = datetime(todayYear, todayMonth, todayDay)
            if datetimeToday > datetimeCode:
                status = self.ExpiredCode
                self.d_redeemCodeResult(avId, context, status)
                return

        if avId in items['UsedBy']:
            status = self.Ineligible
            self.d_redeemCodeResult(avId, context, status)
            return

        # Update the list of avatars that has used this code.
        items['UsedBy'].append(avId)
        self.air.mongoInterface.updateCode(code, items)

        itemList = []

        for item in items['Items']:
            itemType, itemId = item[0], item[1]

            item = globals()[itemType]

            if item == CatalogBeanItem:
                itemList.append(item(itemId, tagCode = 2))
            elif item == CatalogClothingItem:
                itemList.append(item(itemId, 0))

        for item in itemList:
            if len(av.mailboxContents) + len(av.onGiftOrder) >= ToontownGlobals.MaxMailboxContents:
                break

            item.deliveryDate = int(time.time() / 60) + 1

            av.onOrder.append(item)
            av.b_setDeliverySchedule(av.onOrder)

        # Send the response to the client.
        self.d_redeemCodeResult(avId, context, self.Success)

    def d_redeemCodeResult(self, avId: int, context: int, status: int):
        self.sendUpdateToAvatar(avId, 'redeemCodeResult', [context, status, 0])

class SafeZoneManagerAI(DistributedObjectAI):

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.healFrequency = 30
        self.healAmount = 1

    def enterSafeZone(self):
        senderId = self.air.currentAvatarSender
        sender = self.air.doTable.get(senderId)

        if sender:
            sender.startToonUp(self.healFrequency, self.healAmount)

    def exitSafeZone(self):
        senderId = self.air.currentAvatarSender
        sender = self.air.doTable.get(senderId)

        if sender:
            sender.stopToonUp()

class DistributedDeliveryManagerAI(DistributedObjectGlobalAI):
    doId = OTP_DO_ID_TOONTOWN_DELIVERY_MANAGER

    def sendDeliverGifts(self, avId, now):
        if not avId:
            return

        av = self.air.doTable.get(avId)

        if not av:
            return

        _, remainingGifts = av.onGiftOrder.extractDeliveryItems(now)
        av.sendUpdate('setGiftSchedule', [remainingGifts.getBlob(store = CatalogItem.Customization | CatalogItem.DeliveryDate)])