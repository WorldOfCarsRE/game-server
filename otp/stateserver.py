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

        self.handle_location_change(parentId, zoneId, sender)
        self.subscribe_channel(doId)

    def appendRequiredData(self, dg, clientOnly, alsoOwner):
        dg.add_uint32(self.doId)
        dg.add_uint32(self.parentId)
        dg.add_uint32(self.zoneId)
        if not self.dclass:
            print('dclass is none for object id', self.doId)
            return

        dg.add_uint16(self.dclass.getNumber())

        fieldPacker = DCPacker()

        for fieldIndex in range(self.dclass.getNumInheritedFields()):
            field = self.dclass.getInheritedField(fieldIndex)

            if field.isRequired() and not field.asMolecularField() and not clientOnly or field.isBroadcast() or field.isClrecv() or (alsoOwner and field.isOwnrecv()):
                fieldPacker.beginPack(field)

                if self.required and field.getName() in self.required:
                    field.packArgs(fieldPacker, self.required[field.getName()])

                fieldPacker.endPack()

                dg.appendData(fieldPacker.getBytes())

    def appendOtherData(self, dg, clientOnly, alsoOwner):
        if clientOnly:
            fieldsData = Datagram()

            count = 0
            for fieldName, rawData in self.ram.items():
                field = self.dclass.getFieldByName[fieldName]
                if field.is_broadcast or field.isClrecv() or (alsoOwneeer and field.isOwnrecv()):
                    fieldsData.addUint16(field.getNumber())
                    fieldsData.appendData(rawData)
                    count += 1

            dg.addUint16(count)
            if count:
                dg.appendData(fieldsData.getMessage())

        else:
            dg.addUint16(len(self.ram))
            for fieldName, rawData in self.ram.items():
                field = self.dclass.getFieldByName(fieldName)
                dg.addUint16(field.getNumber())
                dg.appendData(rawData)

    def sendInterestEntry(self, location, context):
        pass

    def sendLocationEntry(self, location):
        dg = Datagram()
        addServerHeader(dg, [location], self.doId, STATESERVER_OBJECT_ENTERZONE_WITH_REQUIRED_OTHER)
        dg.add_uint8(bool(self.ram))
        self.appendRequiredData(dg, True, False)
        if self.ram:
            self.appendOtherData(dg, True, False)
        self.service.send_datagram(dg)

    def sendAIEntry(self, location):
        dg = Datagram()
        addServerHeader(dg, [location], self.doId, STATESERVER_OBJECT_ENTER_AI_RECV)
        self.appendRequiredData(dg, False, False)

        if self.ram:
            self.appendOtherData(dg, False, False)

        self.service.send_datagram(dg)

    def send_owner_entry(self, location):
        dg = Datagram()
        addServerHeader(dg, [location], self.doId, STATESERVER_OBJECT_ENTER_OWNER_RECV)
        self.appendRequiredData(dg, False, True)

        if self.ram:
            self.appendOtherData(dg, True, True)

        self.service.send_datagram(dg)

    def handle_location_change(self, new_parent, new_zone, sender):
        old_parent = self.parentId
        old_zone = self.zoneId

        targets = list()

        if self.aiChannel is not None:
            targets.append(self.aiChannel)

        if self.ownerChannel is not None:
            targets.append(self.ownerChannel)

        if new_parent == self.doId:
            raise Exception('Object cannot be parented to itself.\n')

        if new_parent != old_parent:
            if old_parent:
                self.unsubscribe_channel(parent_to_children(old_parent))
                targets.append(old_parent)
                targets.append(location_as_channel(old_parent, old_zone))

            self.parentId = new_parent
            self.zoneId = new_zone

            if new_parent:
                self.subscribe_channel(parent_to_children(new_parent))

                if not self.aiExplicitlySet:
                    newAIChannel = self.service.resolveAIChannel(new_parent)
                    if newAIChannel != self.aiChannel:
                        self.aiChannel = newAIChannel
                        self.sendAIEntry(newAIChannel)

                targets.append(new_parent)

        elif new_zone != old_zone:
            self.zoneId = new_zone

            targets.append(self.parentId)
            targets.append(location_as_channel(self.parentId, old_zone))
        else:
            # Not changing zones.
            return

        dg = Datagram()
        addServerHeader(dg, targets, sender, STATESERVER_OBJECT_CHANGE_ZONE)

        dg.addUint32(self.doId)
        dg.addUint32(new_parent)
        dg.addUint32(new_zone)
        dg.addUint32(old_parent)
        dg.addUint32(old_zone)

        self.service.send_datagram(dg)

        self.parentSynced = False

        if new_parent:
            self.sendLocationEntry(location_as_channel(new_parent, new_zone))

    def handle_ai_change(self, new_ai, sender, channel_is_explicit):
        pass

    def annihilate(self, sender, notifyParent = True):
        targets = list()

        if self.parentId:
            targets.append(location_as_channel(self.parentId, self.zoneId))

            if notifyParent:
                dg = Datagram()
                addServerHeader(dg, [self.parentId], sender, STATESERVER_OBJECT_CHANGE_ZONE)
                dg.add_uint32(self.doId)
                dg.add_uint32(0) # New parent
                dg.add_uint32(0) # new zone
                dg.add_uint32(self.parentId) # old parent
                dg.add_uint32(self.zoneId) # old zone
                self.service.send_datagram(dg)

        if self.ownerChannel:
            targets.append(self.ownerChannel)
        if self.aiChannel:
            targets.append(self.aiChannel)

        dg = Datagram()
        addServerHeader(dg, targets, sender, STATESERVER_OBJECT_DELETE_RAM)
        dg.add_uint32(self.doId)
        self.service.send_datagram(dg)

        self.deleteChildren(sender)

        del self.service.objects[self.doId]

        self.service.remove_participant(self)

        if self.db:
            self.service.databaseObjects.remove(self.doId)

        self.service.log.debug(f'Object {self.doId} has been deleted.')

    def deleteChildren(self, sender):
        pass

    def handleOneUpdate(self, dgi, sender):
        fieldId = dgi.getUint16()
        field = self.dclass.getFieldByIndex(fieldId)
        pos = dgi.getCurrentIndex()

        fieldPacker = DCPacker()
        fieldPacker.setUnpackData(dgi.getDatagram().getMessage()[pos:])

        molecular = field.asMolecularField()

        if molecular:
            for i in range(molecular.getNumAtomics()):
                atomic = molecular.getAtomic(i)

                fieldPacker.beginUnpack(atomic)
                data = atomic.unpackArgs(fieldPacker)
                fieldPacker.endUnpack()

                self.saveField(atomic, data)
        else:
            fieldPacker.beginUnpack(field)
            data = field.unpackArgs(fieldPacker)
            fieldPacker.endUnpack()

            self.saveField(field, data)

        targets = []

        if field.isBroadcast():
            targets.append(location_as_channel(self.parentId, self.zoneId))
        if field.isAirecv() and self.aiChannel and self.aiChannel != sender:
            targets.append(self.aiChannel)
        if field.isOwnrecv() and self.ownerChannel and self.ownerChannel != sender:
            targets.append(self.ownerChannel)

        if targets:
            dg = Datagram()
            addServerHeader(dg, targets, sender, STATESERVER_OBJECT_UPDATE_FIELD)
            dg.addUint32(self.doId)
            dg.addUint16(fieldId)
            dg.appendData(fieldPacker.getBytes())
            self.service.send_datagram(dg)

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
            dg.appendData(data)
            self.service.send_datagram(dg)
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

    def handle_datagram(self, dg, dgi):
        sender = dgi.getInt64()
        msgtype = dgi.getUint16()

        if msgtype == STATESERVER_OBJECT_DELETE_RAM:
            doId = dgi.get_uint32()
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
            new_parent = dgi.getUint32()
            new_zone = dgi.getUint32()
            self.handle_location_change(new_parent, new_zone, sender)
        elif msgtype == STATESERVER_OBJECT_CHANGE_ZONE:
            childId = dgi.getUint32()
            new_parent = dgi.getUint32()
            new_zone = dgi.getUint32()
            old_parent = dgi.getUint32()
            old_zone = dgi.getUint32()

            if new_parent == self.doId:
                if old_parent == self.doId:
                    if new_zone == old_zone:
                        return

                    children = self.zoneObjects[old_zone]
                    children.remove(childId)

                    if not len(children):
                        del self.zoneObjects[old_zone]

                if new_zone not in self.zoneObjects:
                    self.zoneObjects[new_zone] = set()

                self.zoneObjects[new_zone].add(childId)
            elif old_parent == self.doId:
                children = self.zoneObjects[old_zone]
                children.remove(childId)

                if not len(children):
                    del self.zoneObjects[old_zone]
        elif msgtype == STATESERVER_QUERY_ZONE_OBJECT_ALL:
            self.handle_query_zone(dgi, sender)
        elif msgtype == STATESERVER_QUERY_OBJECT_ALL:
            self.handle_query_all(dgi, sender)

    def handle_query_all(self, dgi, sender):
        other = dgi.getUint8()
        context = dgi.getUint32()

        resp = Datagram()
        resp.add_server_header([sender], self.doId, STATESERVER_QUERY_OBJECT_ALL_RESP)
        resp.add_uint32(self.doId)
        resp.add_uint16(context)
        self.appendRequiredData(resp, False, True)
        self.service.send_datagram(resp)

    def handle_query_zone(self, dgi, sender):
        # STATESERVER_QUERY_ZONE_OBJECT_ALL_DONE
        handle = dgi.get_uint16()
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
        resp.add_uint16(handle)
        resp.add_uint32(contextId)

        if not len(objectIds):
            self.service.send_datagram(resp)
            return

        self.sendLocationEntry(sender)

        for doId in objectIds:
            self.service.objects[doId].sendLocationEntry(sender)

        self.service.send_datagram(resp)

class StateServerProtocol(MDUpstreamProtocol):
    def handle_datagram(self, dg, dgi):
        sender = dgi.getInt64()
        msgtype = dgi.getUint16()
        self.service.log.debug(f'State server directly received msgtype {MSG_TO_NAME_DICT[msgtype]} from {sender}.')

        if msgtype == STATESERVER_OBJECT_GENERATE_WITH_REQUIRED:
            self.handle_generate(dgi, sender, False)
        elif msgtype == STATESERVER_OBJECT_GENERATE_WITH_REQUIRED_OTHER:
            self.handle_generate(dgi, sender, True)
        elif msgtype == STATESERVER_OBJECT_CREATE_WITH_REQUIRED_CONTEXT: # DBSS msg
            self.handleDBGenerate(dgi, sender, False)
        elif msgtype == STATESERVER_OBJECT_CREATE_WITH_REQUIR_OTHER_CONTEXT: # DBSS msg
            self.handleDBGenerate(dgi, sender, True)
        elif msgtype == STATESERVER_ADD_AI_RECV:
            self.handle_add_ai(dgi, sender)
        elif msgtype == STATESERVER_OBJECT_SET_OWNER_RECV:
            self.handle_set_owner(dgi, sender)
        elif msgtype == DBSERVER_GET_STORED_VALUES_RESP:
            self.activate_callback(dgi)
        elif msgtype == STATESERVER_SHARD_REST:
            self.handle_shard_rest(dgi)
        elif msgtype == STATESERVER_OBJECT_LOCATE:
            context = dgi.getUint32()
            doId = dgi.getUint32()

            do = self.service.objects.get(do_id)

            resp = Datagram()
            addServerHeader(resp, [sender], do_id, STATESERVER_OBJECT_LOCATE_RESP)
            resp.addUint32(context)
            resp.addUint32(doId)

            if do is None:
                resp.add_uint8(False)
                self.service.send_datagram(resp)
            else:
                resp.add_uint8(True)
                parentId, zoneId = do.parentId, do.zoneId
                resp.addUint32(parentId)
                resp.addUint32(zoneId)
                aiChannel = do.aiChannel if do.aiChannel else 0
                resp.addUint32(aiChannel)
                self.service.send_datagram(resp)

    def handleDBGenerate(self, dgi, sender, other = False):
        doId = dgi.getUint32()

        if doId in self.service.queries or doId in self.service.databaseObjects:
            self.service.log.debug(f'Got duplicate activate request for object {doId} from {sender}')
            return

        parentId = dgi.getUint32()
        zoneId = dgi.getUint32()
        ownerChannel = dgi.getInt64()
        number = dgi.getUint16()

        other_data = []

        stateServer = self.service

        if other:
            fieldCount = dgi.getUint16()

            for i in range(fieldCount):
                fieldNumber = dgi.getUint16()
                field = stateServer.dcFile.getFieldByIndex(fieldNumber)
                data = field.unpack_bytes(dgi)
                other_data.append((fieldNumber, data))

        dclass = stateServer.dcFile.getClass(number)

        query = Datagram()
        addServerHeader(query, [DBSERVERS_CHANNEL], STATESERVERS_CHANNEL, DBSERVER_GET_STORED_VALUES)
        query.add_uint32(1)
        query.add_uint32(doId)

        pos = query.getCurrentIndex()
        query.add_uint16(0)
        count = 0
        for field in dclass:
            if not isinstance(field, MolecularField) and field.is_db:
                if field.getName() == 'DcObjectType':
                    continue
                query.add_uint16(field.getNumber())
                count += 1
        query.seek(pos)
        query.add_uint16(count)

        self.service.log.debug(f'Querying {count} fields for {dclass.name} {doId}. Other data: {other_data}')

        self.service.queries[doId] = (parentId, zoneId, ownerChannel, number, other_data)
        self.service.send_datagram(query)

    def activate_callback(self, dgi):
        context = dgi.get_uint32()
        doId = dgi.get_uint32()

        stateServer = self.service

        parentId, zoneId, ownerChannel, number, other_data = stateServer.queries[doId]
        dclass = stateServer.dcFile.getClass(number)

        del stateServer.queries[doId]

        required = {}
        ram = {}

        count = dgi.getUint16()

        for i in range(count):
            fieldNumber = dgi.getUint16()
            field = stateServer.dcFile.getFieldByIndex(fieldNumber)

            if field.isRequired():
                required[field.getName()] = field.unpack_bytes(dgi)
            else:
                ram[field.getName()] = field.unpack_bytes(dgi)

        for fieldNumber, data in other_data:
            field = stateServer.dcFile.fields[fieldNumber]()
            if field.isRequired():
                required[field.getName()] = data
            else:
                ram[field.getName()] = data

            if field.isDb():
                dg = Datagram()
                dg.add_server_header([DBSERVERS_CHANNEL], doId, DBSERVER_SET_STORED_VALUES)
                dg.add_uint32(do_id)
                dg.add_uint16(1)
                dg.add_uint16(field.getNumber())
                dg.add_bytes(data)
                self.service.send_datagram(dg)

        self.service.log.debug(f'Activating {doId} with required:{required}\nram:{ram}\n')

        obj = DistributedObject(stateServer, STATESERVERS_CHANNEL, doId, parentId, zoneId, dclass, required, ram,
                                ownerChannel = ownerChannel, db = True)
        stateServer.databaseObjects.add(doId)
        stateServer.objects[doId] = obj
        obj.send_owner_entry(ownerChannel)

    def handle_add_ai(self, dgi, sender):
        objectId = dgi.getUint32()
        aiChannel = dgi.getInt64()
        stateServer = self.service
        obj = stateServer.objects[objectId]
        obj.aiChannel = aiChannel
        obj.aiExplicitlySet = True
        print('AI SET FOR', objectId, 'TO', aiChannel)
        obj.sendAIEntry(aiChannel)

    def handle_set_owner(self, dgi, sender):
        objectId = dgi.getUint32()
        ownerChannel = dgi.getInt64()
        stateServer = self.service
        obj = stateServer.objects[objectId]
        obj.ownerChannel = ownerChannel
        obj.sendOwnerEntry(ownerChannel)

    def handle_generate(self, dgi, sender, other = False):
        parentId = dgi.get_uint32()
        zoneId = dgi.get_uint32()
        number = dgi.get_uint16()
        doId = dgi.get_uint32()

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

        fieldPacker = DCPacker()
        fieldPacker.setUnpackData(dgi.getRemainingBytes())

        for fieldIndex in range(dclass.getNumInheritedFields()):
            field = dclass.getInheritedField(fieldIndex)

            if field.asMolecularField():
                continue

            if not field.isRequired():
                continue

            fieldPacker.beginUnpack(field)
            fieldArgs = field.unpackArgs(fieldPacker)
            fieldPacker.endUnpack()

            required[field.getName()] = fieldArgs

        if other:
            numOptionalFields = dgi.get_uint16()

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

    def handle_shard_rest(self, dgi):
        aiChannel = dgi.getInt64()

        for objectId in list(self.service.objects.keys()):
            obj = self.service.objects[objectId]
            if obj.aiChannel == aiChannel:
                obj.annihilate(aiChannel)

from panda3d.direct import DCFile

class StateServer(DownstreamMessageDirector, ChannelAllocator):
    upstream_protocol = StateServerProtocol
    serviceChannels = []
    rootObjectId = OTP_DO_ID_TOONTOWN

    min_channel = 100000000
    max_channel = 399999999

    def __init__(self, loop):
        DownstreamMessageDirector.__init__(self, loop)
        ChannelAllocator.__init__(self)

        self.dcFile = DCFile()
        self.dcFile.read('etc/dclass/toon.dc')

        self.loop.set_exception_handler(self._on_exception)

        self.objects: Dict[int, DistributedObject] = {}
        self.databaseObjects = set()
        self.queries = {}

    def _on_exception(self, loop, context):
        print('err', context)

    async def run(self):
        await self.connect(config['MessageDirector.HOST'], config['MessageDirector.PORT'])
        await self.route()

    def on_upstream_connect(self):
        self.subscribe_channel(self._client, STATESERVERS_CHANNEL)
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