from otp import config

import asyncio

from otp.messagedirector import MDUpstreamProtocol, DownstreamMessageDirector
from panda3d.core import Datagram, DatagramIterator
from otp.constants import STATESERVERS_CHANNEL
from otp.messagetypes import *
from otp.messagedirector import MDParticipant
from otp.networking import ChannelAllocator
from otp.constants import *
from panda3d.direct import DCPacker
from otp.util import addServerHeader

from typing import Dict, Set

from otp.zone import *

class DistributedObject(MDParticipant):
    def __init__(self, stateServer, sender, doId, parentId, zoneId, dclass, required, ram, ownerChannel = None, db = False):
        MDParticipant.__init__(self, stateServer)
        self.sender = sender
        self.doId = doId
        self.parentId = 0
        self.zoneId = 0
        self.dclass = dclass
        self.required = required
        self.ram = ram
        self.db = db

        self.aiChannel = None
        self.ownerChannel = ownerChannel

        self.aiExplicitlySet = False
        self.parentSynced = False
        self.nextContext = 0
        self.zoneObjects: Dict[int, Set[int]] = {}

        if self.dclass:
            self.service.log.debug(f'Generating new object {doId} with dclass {self.dclass.getName()} in location {parentId} {zoneId}')

        self.handleLocationChange(parentId, zoneId, sender)
        self.subscribeChannel(doId)

    def appendRequiredData(self, dg, clientOnly, alsoOwner):
        dg.addUint32(self.doId)
        dg.addUint32(self.parentId)
        dg.addUint32(self.zoneId)
        if not self.dclass:
            print('dclass is none for object id', self.doId)
            return

        dg.addUint16(self.dclass.getNumber())

        for fieldIndex in range(self.dclass.getNumInheritedFields()):
            field = self.dclass.getInheritedField(fieldIndex)
            if field.asMolecularField():
                continue
            if not field.isRequired():
                continue

            if not clientOnly or field.isBroadcast() or field.isClrecv() or (alsoOwner and field.isOwnrecv()):
                fieldPacker = DCPacker()
                fieldPacker.beginPack(field)

                field.packArgs(fieldPacker, self.required[field.getName()])
                fieldPacker.endPack()

                dg.appendData(fieldPacker.getBytes())

    def appendOtherData(self, dg, clientOnly, alsoOwner):
        if clientOnly:
            packer = DCPacker()

            count = 0
            for fieldName, rawData in self.ram.items():
                field = self.dclass.getFieldByName(fieldName)
                if field.isBroadcast() or field.isClrecv() or (alsoOwner and field.isOwnrecv()):
                    packer.rawPackUint16(field.getNumber())
                    packer.beginPack(field)
                    field.packArgs(packer, rawData)
                    packer.endPack()
                    count += 1

            dg.addUint16(count)
            if count:
                dg.appendData(packer.getBytes())

        else:
            dg.addUint16(len(self.ram))

            for fieldName, rawData in self.ram.items():
                field = self.dclass.getFieldByName(fieldName)
                otherPacker = DCPacker()

                dg.addUint16(field.getNumber())

                otherPacker.beginPack(field)
                field.packArgs(otherPacker, rawData)
                otherPacker.endPack()

                dg.appendData(otherPacker.getBytes())

    def sendInterestEntry(self, location, context):
        pass

    def sendLocationEntry(self, location):
        dg = Datagram()
        addServerHeader(dg, [location], self.doId, STATESERVER_OBJECT_ENTERZONE_WITH_REQUIRED_OTHER)
        dg.addUint8(bool(self.ram))
        self.appendRequiredData(dg, True, False)
        if self.ram:
            self.appendOtherData(dg, True, False)
        self.service.sendDatagram(dg)

    def sendAIEntry(self, location):
        dg = Datagram()
        addServerHeader(dg, [location], self.doId, STATESERVER_OBJECT_ENTER_AI_RECV)
        self.appendRequiredData(dg, False, False)

        if self.ram:
            self.appendOtherData(dg, False, False)

        self.service.sendDatagram(dg)

    def sendOwnerEntry(self, location):
        dg = Datagram()
        addServerHeader(dg, [location], self.doId, STATESERVER_OBJECT_ENTER_OWNER_RECV)
        self.appendRequiredData(dg, False, True)

        if self.ram:
            self.appendOtherData(dg, True, True)

        self.service.sendDatagram(dg)

    def handleLocationChange(self, newParent, newZone, sender):
        oldParent = self.parentId
        oldZone = self.zoneId

        targets = list()

        if self.aiChannel is not None:
            targets.append(self.aiChannel)

        if self.ownerChannel is not None:
            targets.append(self.ownerChannel)

        if newParent == self.doId:
            raise Exception('Object cannot be parented to itself.\n')

        if newParent != oldParent:
            if oldParent:
                self.unsubscribeChannel(parentToChildren(oldParent))
                targets.append(oldParent)
                targets.append(locationAsChannel(oldParent, oldZone))

            self.parentId = newParent
            self.zoneId = newZone

            if newParent:
                self.subscribeChannel(parentToChildren(newParent))

                if not self.aiExplicitlySet:
                    newAIChannel = self.service.resolveAIChannel(newParent)
                    if newAIChannel != self.aiChannel:
                        self.aiChannel = newAIChannel
                        self.sendAIEntry(newAIChannel)

                targets.append(newParent)

        elif newZone != oldZone:
            self.zoneId = newZone

            targets.append(self.parentId)
            targets.append(locationAsChannel(self.parentId, oldZone))
        else:
            # Not changing zones.
            return

        dg = Datagram()
        addServerHeader(dg, targets, sender, STATESERVER_OBJECT_CHANGE_ZONE)

        dg.addUint32(self.doId)
        dg.addUint32(newParent)
        dg.addUint32(newZone)
        dg.addUint32(oldParent)
        dg.addUint32(oldZone)

        self.service.sendDatagram(dg)

        self.parentSynced = False

        if newParent:
            self.sendLocationEntry(locationAsChannel(newParent, newZone))

    def handleAIChange(self, new_ai, sender, channel_is_explicit):
        pass

    def annihilate(self, sender, notifyParent = True):
        targets = list()

        if self.parentId:
            targets.append(locationAsChannel(self.parentId, self.zoneId))

            if notifyParent:
                dg = Datagram()
                addServerHeader(dg, [self.parentId], sender, STATESERVER_OBJECT_CHANGE_ZONE)
                dg.addUint32(self.doId)
                dg.addUint32(0) # New parent
                dg.addUint32(0) # new zone
                dg.addUint32(self.parentId) # old parent
                dg.addUint32(self.zoneId) # old zone
                self.service.sendDatagram(dg)

        if self.ownerChannel:
            targets.append(self.ownerChannel)
        if self.aiChannel:
            targets.append(self.aiChannel)

        dg = Datagram()
        addServerHeader(dg, targets, sender, STATESERVER_OBJECT_DELETE_RAM)
        dg.addUint32(self.doId)
        self.service.sendDatagram(dg)

        self.deleteChildren(sender)

        del self.service.objects[self.doId]

        self.service.removeParticipant(self)

        if self.db:
            self.service.databaseObjects.remove(self.doId)

        self.service.log.debug(f'Object {self.doId} has been deleted.')

    def deleteChildren(self, sender):
        pass

    def handleOneUpdate(self, dgi, sender):
        fieldId = dgi.getUint16()
        field = self.dclass.getFieldByIndex(fieldId)
        pos = dgi.getCurrentIndex()
        _data = dgi.getDatagram().getMessage()[pos:]

        unpacker = DCPacker()
        unpacker.setUnpackData(_data)

        molecular = field.asMolecularField()

        if molecular:
            for i in range(molecular.getNumAtomics()):
                atomic = molecular.getAtomic(i)

                unpacker.beginUnpack(atomic)
                data = atomic.unpackArgs(unpacker)
                unpacker.endUnpack()

                self.saveField(atomic, data)
        else:
            unpacker.beginUnpack(field)
            data = field.unpackArgs(unpacker)
            unpacker.endUnpack()

            self.saveField(field, data)

        targets = []

        if field.isBroadcast():
            targets.append(locationAsChannel(self.parentId, self.zoneId))
        if field.isAirecv() and self.aiChannel and self.aiChannel != sender:
            targets.append(self.aiChannel)
        if field.isOwnrecv() and self.ownerChannel and self.ownerChannel != sender:
            targets.append(self.ownerChannel)

        if targets:
            dg = Datagram()
            addServerHeader(dg, targets, sender, STATESERVER_OBJECT_UPDATE_FIELD)
            dg.addUint32(self.doId)
            dg.addUint16(fieldId)
            dg.appendData(_data)
            self.service.sendDatagram(dg)

    def saveField(self, field, data):
        if field.isRequired():
            self.required[field.getName()] = data
        elif field.isRam():
            self.ram[field.getName()] = data

        if self.db and field.isDb():
            dg = Datagram()
            addServerHeader(dg, [DBSERVERS_CHANNEL], self.doId, DBSERVER_SET_STORED_VALUES)
            dg.addUint32(self.doId)
            dg.addUint16(1)
            dg.addUint16(field.getNumber())

            packer = DCPacker()
            packer.beginPack(field)
            field.packArgs(packer, data)
            packer.endPack()

            dg.appendData(packer.getBytes())

            self.service.sendDatagram(dg)
            self.service.log.debug(f'Object {self.doId} saved value {data} for field {field.getName()} to database.')

    def handleOneGet(self, dg, fieldId, subfield = False):
        field = self.dclass.getFieldByIndex(fieldId)

        if field.asMolecularField():
            if not subfield:
                dg.addUint16(fieldId)
            for field in field.subfields:
                self.handleOneGet(dg, field.getNumber(), subfield)

        if field.getName() in self.required:
            dg.append_data(self.required[field.getName()])
        elif field.getName() in self.ram:
            dg.append_data(self.ram[field.getName()])

    def handleDatagram(self, dg, dgi):
        sender = dgi.getInt64()
        msgtype = dgi.getUint16()

        if msgtype == STATESERVER_OBJECT_DELETE_RAM:
            doId = dgi.getUint32()
            if doId == self.doId or doId == self.parentId:
                self.annihilate(sender)
                return
        elif msgtype == STATESERVER_OBJECT_UPDATE_FIELD:
            if self.doId != dgi.getUint32():
                return
            self.handleOneUpdate(dgi, sender)
        elif msgtype == STATESERVER_OBJECT_UPDATE_FIELD_MULTIPLE:
            if self.doId != dgi.getUint32():
                return

            fieldCount = dgi.getUint16()
            for i in range(fieldCount):
                self.handleOneUpdate(dgi, sender)
        elif msgtype == STATESERVER_OBJECT_SET_ZONE:
            newParent = dgi.getUint32()
            newZone = dgi.getUint32()
            self.handleLocationChange(newParent, newZone, sender)
        elif msgtype == STATESERVER_OBJECT_CHANGE_ZONE:
            childId = dgi.getUint32()
            newParent = dgi.getUint32()
            newZone = dgi.getUint32()
            oldParent = dgi.getUint32()
            oldZone = dgi.getUint32()

            if newParent == self.doId:
                if oldParent == self.doId:
                    if newZone == oldZone:
                        return

                    children = self.zoneObjects[oldZone]
                    children.remove(childId)

                    if not len(children):
                        del self.zoneObjects[oldZone]

                if newZone not in self.zoneObjects:
                    self.zoneObjects[newZone] = set()

                self.zoneObjects[newZone].add(childId)
            elif oldParent == self.doId:
                children = self.zoneObjects[oldZone]
                children.remove(childId)

                if not len(children):
                    del self.zoneObjects[oldZone]
        elif msgtype == STATESERVER_QUERY_ZONE_OBJECT_ALL:
            self.handleQueryZone(dgi, sender)
        elif msgtype == STATESERVER_QUERY_OBJECT_ALL:
            self.handleQueryAll(dgi, sender)

    def handleQueryAll(self, dgi, sender):
        other = dgi.getUint8()
        context = dgi.getUint32()

        resp = Datagram()
        addServerHeader(resp, [sender], self.doId, STATESERVER_QUERY_OBJECT_ALL_RESP)
        resp.addUint32(self.doId)
        resp.addUint16(context)
        self.appendRequiredData(resp, False, True)
        self.service.sendDatagram(resp)

    def handleQueryZone(self, dgi, sender):
        # STATESERVER_QUERY_ZONE_OBJECT_ALL_DONE
        handle = dgi.getUint16()
        contextId = dgi.getUint32()
        parentId = dgi.getUint32()

        if parentId != self.doId:
            return

        numZones = dgi.getRemainingSize() // 4

        zones = []

        for i in range(numZones):
            zones.append(dgi.getUint32())

        objectIds = []

        for zone in zones:
            if zone not in self.zoneObjects:
                continue

            objectIds.extend(self.zoneObjects[zone])

        resp = Datagram()
        addServerHeader(resp, [sender], self.doId, STATESERVER_QUERY_ZONE_OBJECT_ALL_DONE)
        resp.addUint16(handle)
        resp.addUint32(contextId)

        if not len(objectIds):
            self.service.sendDatagram(resp)
            return

        self.sendLocationEntry(sender)

        for doId in objectIds:
            self.service.objects[doId].sendLocationEntry(sender)

        self.service.sendDatagram(resp)

class StateServerProtocol(MDUpstreamProtocol):
    def handleDatagram(self, dg, dgi):
        sender = dgi.getInt64()
        msgtype = dgi.getUint16()
        self.service.log.debug(f'State server directly received msgtype {MSG_TO_NAME_DICT[msgtype]} from {sender}.')

        if msgtype == STATESERVER_OBJECT_GENERATE_WITH_REQUIRED:
            self.handleGenerate(dgi, sender, False)
        elif msgtype == STATESERVER_OBJECT_GENERATE_WITH_REQUIRED_OTHER:
            self.handleGenerate(dgi, sender, True)
        elif msgtype == STATESERVER_OBJECT_CREATE_WITH_REQUIRED_CONTEXT: # DBSS msg
            self.handleDBGenerate(dgi, sender, False)
        elif msgtype == STATESERVER_OBJECT_CREATE_WITH_REQUIR_OTHER_CONTEXT: # DBSS msg
            self.handleDBGenerate(dgi, sender, True)
        elif msgtype == STATESERVER_ADD_AI_RECV:
            self.handleAddAI(dgi, sender)
        elif msgtype == STATESERVER_OBJECT_SET_OWNER_RECV:
            self.handleSetOwner(dgi, sender)
        elif msgtype == DBSERVER_GET_STORED_VALUES_RESP:
            self.activeCallback(dgi)
        elif msgtype == STATESERVER_SHARD_REST:
            self.handleShardRest(dgi)
        elif msgtype == STATESERVER_OBJECT_LOCATE:
            context = dgi.getUint32()
            doId = dgi.getUint32()

            do = self.service.objects.get(doId)

            resp = Datagram()
            addServerHeader(resp, [sender], doId, STATESERVER_OBJECT_LOCATE_RESP)
            resp.addUint32(context)
            resp.addUint32(doId)

            if do is None:
                resp.addUint8(False)
                self.service.sendDatagram(resp)
            else:
                resp.addUint8(True)
                parentId, zoneId = do.parentId, do.zoneId
                resp.addUint32(parentId)
                resp.addUint32(zoneId)
                aiChannel = do.aiChannel if do.aiChannel else 0
                resp.addUint32(aiChannel)
                self.service.sendDatagram(resp)

    def handleDBGenerate(self, dgi, sender, other = False):
        doId = dgi.getUint32()

        if doId in self.service.queries or doId in self.service.databaseObjects:
            self.service.log.debug(f'Got duplicate activate request for object {doId} from {sender}')
            return

        parentId = dgi.getUint32()
        zoneId = dgi.getUint32()
        ownerChannel = dgi.getInt64()
        number = dgi.getUint16()

        otherData = []

        stateServer = self.service

        if other:
            fieldCount = dgi.getUint16()

            unpacker = DCPacker()
            unpacker.setUnpackData(dgi.getRemainingBytes())

            for i in range(fieldCount):
                fieldNum = unpacker.rawUnpackUint16()
                field = stateServer.dcFile.getFieldByIndex(fieldNum)

                unpacker.beginUnpack(field)

                data = field.unpackArgs(unpacker)

                unpacker.endUnpack()

                otherData.append((fieldNum, data))

        dclass = stateServer.dcFile.getClass(number)

        query = Datagram()
        addServerHeader(query, [DBSERVERS_CHANNEL], STATESERVERS_CHANNEL, DBSERVER_GET_STORED_VALUES)
        query.addUint32(1)
        query.addUint32(doId)

        count = 0

        for fieldId in range(dclass.getNumInheritedFields()):
            field = dclass.getInheritedField(fieldId)

            if not field.asMolecularField() and field.isDb():
                if field.getName() == 'DcObjectType':
                    continue
                query.addUint16(field.getNumber())
                count += 1

        self.service.log.debug(f'Querying {count} fields for {dclass.getName()} {doId}. Other data: {otherData}')

        self.service.queries[doId] = (parentId, zoneId, ownerChannel, number, otherData)
        self.service.sendDatagram(query)

    def activeCallback(self, dgi):
        context = dgi.getUint32()
        doId = dgi.getUint32()

        stateServer = self.service

        parentId, zoneId, ownerChannel, number, otherData = stateServer.queries[doId]
        dclass = stateServer.dcFile.getClass(number)

        del stateServer.queries[doId]

        required = {}
        ram = {}

        count = dgi.getUint16()

        for i in range(count):
            fieldNumber = dgi.getUint16()
            field = stateServer.dcFile.getFieldByIndex(fieldNumber)

            unpacker = DCPacker()
            unpacker.setUnpackData(dgi.getBlob())

            unpacker.beginUnpack(field)

            data = field.unpackArgs(unpacker)

            if field.isRequired():
                required[field.getName()] = data
            else:
                ram[field.getName()] = data

            unpacker.endUnpack()

        for fieldNumber, data in otherData:
            field = stateServer.dcFile.getFieldByIndex(fieldNumber)

            if field.isRequired():
                required[field.getName()] = data
            else:
                ram[field.getName()] = data

            # Pack the data back up.
            packer = DCPacker()
            packer.beginPack(field)
            field.packArgs(packer, data)
            packer.endPack()

            if field.isDb():
                dg = Datagram()
                addServerHeader(dg, [DBSERVERS_CHANNEL], doId, DBSERVER_SET_STORED_VALUES)
                dg.addUint32(doId)
                dg.addUint16(1)
                dg.addUint16(field.getNumber())
                dg.appendData(packer.getBytes())
                self.service.sendDatagram(dg)

        self.service.log.debug(f'Activating {doId} with required:{required}\nram:{ram}\n')

        obj = DistributedObject(stateServer, STATESERVERS_CHANNEL, doId, parentId, zoneId, dclass, required, ram,
                                ownerChannel = ownerChannel, db = True)
        stateServer.databaseObjects.add(doId)
        stateServer.objects[doId] = obj
        obj.sendOwnerEntry(ownerChannel)

    def handleAddAI(self, dgi, sender):
        objectId = dgi.getUint32()
        aiChannel = dgi.getInt64()
        stateServer = self.service
        obj = stateServer.objects[objectId]
        obj.aiChannel = aiChannel
        obj.aiExplicitlySet = True
        print('AI SET FOR', objectId, 'TO', aiChannel)
        obj.sendAIEntry(aiChannel)

    def handleSetOwner(self, dgi, sender):
        objectId = dgi.getUint32()
        ownerChannel = dgi.getInt64()
        stateServer = self.service
        obj = stateServer.objects[objectId]
        obj.ownerChannel = ownerChannel
        obj.sendOwnerEntry(ownerChannel)

    def handleGenerate(self, dgi, sender, other = False):
        parentId = dgi.getUint32()
        zoneId = dgi.getUint32()
        number = dgi.getUint16()
        doId = dgi.getUint32()

        stateServer = self.service

        if doId in stateServer.objects:
            self.service.log.debug(f'Received duplicate generate for object {doId}')
            return

        if number > stateServer.dcFile.getNumClasses():
            self.service.log.debug(f'Received create for unknown dclass with class id {number}')
            return

        dclass = stateServer.dcFile.getClass(number)

        required = {}
        ram = {}

        unpacker = DCPacker()
        unpacker.setUnpackData(dgi.getRemainingBytes())

        for fieldIndex in range(dclass.getNumInheritedFields()):
            field = dclass.getInheritedField(fieldIndex)

            if field.asMolecularField():
                continue

            if not field.isRequired():
                continue

            unpacker.beginUnpack(field)
            fieldArgs = field.unpackArgs(unpacker)
            unpacker.endUnpack()

            required[field.getName()] = fieldArgs

        if other:
            numOptionalFields = dgi.getUint16()

            for i in range(numOptionalFields):
                fieldNumber = dgi.getUint16()

                field = dclass.getFieldByIndex(fieldNumber)

                if not field.isRam():
                    self.service.log.debug(f'Received non-RAM field {field.getName()} within an OTHER section.\n')
                    field.unpack_bytes(dgi)
                    continue
                else:
                    ram[field.getName()] = field.unpackBytes(dgi)

        obj = DistributedObject(stateServer, sender, doId, parentId, zoneId, dclass, required, ram)
        stateServer.objects[doId] = obj

    def handleShardRest(self, dgi):
        aiChannel = dgi.getInt64()

        for objectId in list(self.service.objects.keys()):
            obj = self.service.objects[objectId]
            if obj.aiChannel == aiChannel:
                obj.annihilate(aiChannel)

from panda3d.direct import DCFile

class StateServer(DownstreamMessageDirector, ChannelAllocator):
    upstreamProtocol = StateServerProtocol
    serviceChannels = []
    rootObjectId = OTP_DO_ID_TOONTOWN

    minChannel = 100000000
    maxChannel = 399999999

    def __init__(self, loop):
        DownstreamMessageDirector.__init__(self, loop)
        ChannelAllocator.__init__(self)

        self.dcFile = DCFile()
        self.dcFile.read('etc/dclass/toon.dc')

        self.loop.set_exception_handler(self.onException)

        self.objects: Dict[int, DistributedObject] = {}
        self.databaseObjects = set()
        self.queries = {}

    def onException(self, loop, context):
        print('err', context)

    async def run(self):
        await self.connect(config['MessageDirector.HOST'], config['MessageDirector.PORT'])
        await self.route()

    def on_upstream_connect(self):
        self.subscribeChannel(self._client, STATESERVERS_CHANNEL)
        self.objects[self.rootObjectId] = DistributedObject(self, STATESERVERS_CHANNEL, self.rootObjectId,
                                                              0, 2, self.dcFile.getClassByName('DistributedDirectory'),
                                                              None, None)

    def resolveAIChannel(self, parentId):
        aiChannel = None

        while aiChannel is None:
            try:
                obj = self.objects[parentId]
                parentId = obj.parentId
                aiChannel = obj.aiChannel
            except KeyError:
                return None

        return aiChannel

async def main():
    loop = asyncio.get_running_loop()
    service = StateServer(loop)
    await service.run()

if __name__ == '__main__':
    asyncio.run(main(), debug = True)