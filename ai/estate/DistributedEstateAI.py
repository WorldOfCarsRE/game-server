from dataslots import with_slots
from dataclasses import dataclass

from ai.DistributedObjectAI import DistributedObjectAI
from ai.house import HouseGlobals
from ai.globals.HoodGlobals import MyEstate
from ai.fishing.FishingAI import DistributedFishingPondAI, DistributedFishingSpotAI

from panda3d.toontown import loadDNAFileAI, DNAStorage

from typing import List
import time

@with_slots
@dataclass
class LawnItem:
    itemType: int
    hardPoint: int
    waterLevel: int
    growthLevel: int
    optional: int

class DistributedEstateAI(DistributedObjectAI):

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.estateType = 0
        self.dawnTime = 0
        self.decorData: List[LawnItem] = []
        self.lastEpochTimestamp = 0
        self.rentalTimestamp = 0
        self.rentalType = 0
        self.lawnItems: List[LawnItem] = [[], [], [], [], [], []]
        self.activeToons = [0, 0, 0, 0, 0, 0]
        self.clouds = 0
        self.ponds = []
        self.spots = []

    def delete(self):
        DistributedObjectAI.delete(self)
        for pond in self.ponds:
            pond.requestDelete()
        del self.ponds
        for spot in self.spots:
            spot.requestDelete()
        del self.spots

    def announceGenerate(self):
        storage = DNAStorage()
        dna = loadDNAFileAI(storage, 'dna/estate_1.dna')

        pondName2Do = {}

        for pondName in storage.ponds:
            group = storage.groups[pondName]
            pond = DistributedFishingPondAI(self.air, MyEstate)
            pond.generateWithRequired(self.zoneId)
            pondName2Do[pondName] = pond
            self.ponds.append(pond)

        for dnaspot in storage.spots:
            group = dnaspot.get_group()
            pondName = dnaspot.get_pond_name()
            pond = pondName2Do[pondName]
            spot = DistributedFishingSpotAI(self.air, pond, group.get_pos_hpr())
            spot.generateWithRequired(pond.zoneId)
            self.spots.append(spot)

        del pondName2Do

        DistributedObjectAI.announceGenerate(self)

    def getEstateType(self) -> int:
        return self.estateType

    def getDawnTime(self) -> int:
        return self.dawnTime

    def getDecorData(self) -> List[LawnItem]:
        return self.decorData

    def getLastEpochTimeStamp(self) -> int:
        return self.lastEpochTimestamp

    def getRentalTimeStamp(self) -> int:
        return self.rentalTimestamp

    def getRentalType(self) -> int:
        return self.rentalType

    def getSlot0ToonId(self) -> int:
        return self.activeToons[0]

    def getSlot0Items(self) -> List[LawnItem]:
        return self.lawnItems[0]

    def getSlot1ToonId(self) -> int:
        return self.activeToons[1]

    def getSlot1Items(self) -> List[LawnItem]:
        return self.lawnItems[1]

    def getSlot2ToonId(self) -> int:
        return self.activeToons[2]

    def getSlot2Items(self) -> List[LawnItem]:
        return self.lawnItems[2]

    def getSlot3ToonId(self) -> int:
        return self.activeToons[3]

    def getSlot3Items(self) -> List[LawnItem]:
        return self.lawnItems[3]

    def getSlot4ToonId(self) -> int:
        return self.activeToons[4]

    def getSlot4Items(self) -> List[LawnItem]:
        return self.lawnItems[4]

    def getSlot5ToonId(self) -> int:
        return self.activeToons[5]

    def getSlot5Items(self) -> List[LawnItem]:
        return self.lawnItems[5]

    def getClouds(self) -> int:
        return self.clouds

    def requestServerTime(self):
        avId = self.air.currentAvatarSender
        self.sendUpdateToAvatar(avId, 'setServerTime', [time.time() % HouseGlobals.DAY_NIGHT_PERIOD])