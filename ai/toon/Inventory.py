from panda3d.core import Datagram, DatagramIterator
from ai.battle.BattleGlobals import *
from typing import Union

class Inventory:
    __slots__ = 'inventory', 'toon'

    def __init__(self, inventory = None, toon = None):
        if not inventory:
            self.inventory = [0] * NUM_TRACKS * NUM_PROPS
        else:
            self.inventory = inventory

        self.toon = toon

    def __getitem__(self, key):
        if not type(key) == int:
            raise IndexError

        return self.inventory[key]

    def __setitem__(self, key, value):
        self.inventory[key] = value

    def __iter__(self):
        yield from self.inventory

    @property
    def totalProps(self):
        return sum(self.inventory)

    def get(self, track: int, level: int) -> int:
        return self[track * NUM_PROPS + level]

    def getMax(self, track, level):
        if self.toon.experience:
            gagTrack = getGagTrack(track)
            expLevel = self.toon.experience.getExpLevel(track)
            return gagTrack.carryLimits[expLevel][level]
        else:
            return 0

    def addItems(self, track, level, amount):
        if not self.toon.hasTrackAccess(track):
            return

        if self.toon.experience.getExpLevel(track) < level:
            return

        if self.totalProps + amount > self.toon.getMaxCarry() and level < 6:
            return

        self[track * NUM_TRACKS + level] += amount
        return self[track * NUM_TRACKS + level]

    def validatePurchase(self, newInventory, currentMoney, newMoney):
        if newMoney > currentMoney:
            return False

        newTotal = newInventory.totalProps
        oldTotal = self.totalProps

        if newTotal > oldTotal + currentMoney:
            return False

        if newTotal - oldTotal > currentMoney - newMoney:
            return False

        if newTotal > self.toon.getMaxCarry():
            print('more than max carry')
            return False

        for i in UBER_LEVELS:
            if newInventory[i] > self[i]:
                # Can't buy level 7 gags.
                print('tried buying uber')
                return False

        if not newInventory.validateItems():
            return False

        # TODO: check access

        return True

    def validateItems(self):
        for index, amount in enumerate(self):
            track, level = index // NUM_TRACKS, index % NUM_PROPS

            if not self.toon.hasTrackAccess(track) and amount:
                print('no track acccess and tried to buy')
                return False

            if amount > self.getMax(track, level):
                print('over max')
                return False

        return True

    def use(self, track: Union[Tracks, int], level: int):
        i = track * NUM_PROPS + level
        if self[i] > 0:
            self[i] -= 1

    @staticmethod
    def fromBytes(data):
        dg = Datagram(data)
        return Inventory.fromNetString(DatagramIterator(dg))

    @staticmethod
    def fromNetString(dgi):
        return Inventory([dgi.getUint8() for _ in range(NUM_TRACKS * NUM_PROPS)])

    def makeNetString(self):
        return b''.join((prop.to_bytes(1, 'little') for prop in self.inventory))

    def zero(self, killUber = False):
        for i in range(NUM_TRACKS * NUM_PROPS):
            if not killUber and (i + 1) % 7 == 0:
                continue
            self[i] = 0