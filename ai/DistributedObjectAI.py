from otp.util import getPuppetChannel, getAccountChannel
from direct.showbase.DirectObject import DirectObject

from . import AIRepository

from .AIZoneData import AIZoneData
from typing import Optional
from collections import deque

class DistributedObjectAI(DirectObject):
    QUIET_ZONE = 1
    doId: Optional[int] = None

    def __init__(self, air: AIRepository.AIRepository):
        DirectObject.__init__(self)
        self.air = air
        self.dclass = air.dcFile.getClassByName(self.__class__.__name__[:-2])
        self.zoneId = 0
        self.parentId = 0

        self._zoneData = None

        self.lastLogicalZoneId = 0
        self.queueUpdates = True
        self.updateQueue = deque()

    def generateWithRequired(self, zoneId):
        self.zoneId = zoneId
        self.air.generateWithRequired(self, self.air.district.doId, zoneId)

    def sendUpdateToChannel(self, channel, fieldName, args):
        dg = self.dclass.aiFormatUpdate(fieldName, self.doId, channel, self.air.ourChannel, args)
        if self.queueUpdates:
            # Avoid race conditions where stateserver has not subscribed to the doId channel on the message director
            # so it misses the field update.
            # print(self.doId, self.__class__.__name__, 'queueing field update', fieldName)
            self.updateQueue.append(dg)
        else:
            self.air.send(dg)

    def sendUpdate(self, fieldName, args):
        self.sendUpdateToChannel(self.doId, fieldName, args)

    def sendUpdateToSender(self, fieldName, args):
        self.sendUpdateToChannel(self.air.currentSender, fieldName, args)

    def sendUpdateToAvatar(self, av_id, fieldName, args):
        self.sendUpdateToChannel(getPuppetChannel(av_id), fieldName, args)

    def sendUpdateToAccount(self, disl_id, fieldName, args):
        self.sendUpdateToChannel(getAccountChannel(disl_id), fieldName, args)

    @property
    def location(self):
        return self.parentId, self.zoneId

    @location.setter
    def location(self, location):
        if location == self.location:
            return
        parentId, zoneId = location
        oldParentId, oldZoneId = self.location
        self.parentId = parentId
        self.zoneId = zoneId

        self.air.storeLocation(self.doId, oldParentId, oldZoneId, parentId, zoneId)

        self.handleZoneChange(oldZoneId, zoneId)

        if zoneId != DistributedObjectAI.QUIET_ZONE:
            self.handleLogicalZoneChange(oldZoneId, zoneId)
            self.lastLogicalZoneId = zoneId

    @property
    def zoneData(self) -> AIZoneData:
        if self._zoneData is None:
            self._zoneData = AIZoneData(self.air, self.parentId, self.zoneId)
        return self._zoneData

    @property
    def render(self):
        return self.zoneData.render

    @property
    def nonCollidableParent(self):
        return self.zoneData.nonCollidableParent

    @property
    def parentMgr(self):
        return self.zoneData.parentMgr

    def releaseZoneData(self):
        if self._zoneData is not None:
            self._zoneData.destroy()
            self._zoneData = None

    def handleLogicalZoneChange(self, old_zone: int, new_zone: int):
        pass

    def generate(self):
        pass

    def announceGenerate(self):
        pass

    def delete(self):
        if self.air:
            self.releaseZoneData()
            if self.doId and self.air.minChannel <= self.doId <= self.air.maxChannel:
                self.air.deallocateChannel(self.doId)
            self.air = None
            self.zoneId = 0
            self.parentId = 0
            if self.doId != None:
                messenger.send('do-deleted-%d' % self.doId)
            self.doId = None

    @property
    def deleted(self):
        return self.air is None

    @property
    def generated(self):
        return self.doId is not None

    def requestDelete(self):
        if not self.doId:
            print(f'Tried deleting {self.__class__.__name__} more than once!')
            return

        self.air.requestDelete(self)

    def uniqueName(self, name, useDoId=True):
        if useDoId:
            return f'{name}-{self.doId}'
        else:
            return f'{name}-{id(self)}'

    def handleChildArrive(self, obj, zoneId):
        pass

    def handleChildArriveZone(self, obj, zoneId):
        pass

    def handleChildLeave(self, obj, zoneId):
        pass

    def handleChildLeaveZone(self, obj, zoneId):
        pass

    def handleZoneChange(self, oldZoneId, zoneId):
        pass

    def sendSetZone(self, newZone: int):
        self.air.sendLocation(self.doId, self.parentId, self.zoneId, self.parentId, newZone)
        self.location = (self.parentId, newZone)
