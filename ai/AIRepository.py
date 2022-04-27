from otp.messagetypes import *
from panda3d.core import Datagram, DatagramIterator
from panda3d.core import SocketAddress, SocketUDPOutgoing
from otp.constants import *
from otp.zone import *
from otp.util import *

from panda3d.core import UniqueIdAllocator
from direct.showbase.MessengerGlobal import *
from panda3d.direct import DCFile, DCPacker
import queue

from typing import Dict, Tuple

from otp.networking import CarsProtocol

from threading import Thread, Event

import asyncio

from . import AIZoneData

from ai.CarsGlobals import DynamicZonesBegin, DynamicZonesEnd
from .MongoInterface import MongoInterface

from importlib import import_module
import time

class AIProtocol(CarsProtocol):
    def connection_made(self, transport):
        CarsProtocol.connection_made(self, transport)
        self.service.connected.set()

    def connection_lost(self, exc):
        raise Exception('AI CONNECTION LOST', exc)

    def receiveDatagram(self, dg):
        self.service.queue.put_nowait(dg)

    def sendDatagram(self, data: Datagram):
        loop = self.service.loop
        loop.call_soon_threadsafe(self.outgoingQ.put_nowait, data.getMessage())

class AIRepository:
    def __init__(self):
        self.connection = None
        self.queue = queue.Queue()

        baseChannel = 4000000

        maxChannels = 1000000
        self.minChannel = baseChannel
        self.maxChannel = baseChannel + maxChannels
        self.channelAllocator = UniqueIdAllocator(self.minChannel, self.maxChannel)
        self.zoneAllocator = UniqueIdAllocator(DynamicZonesBegin, DynamicZonesEnd)

        self._registedChannels = set()

        self.__contextCounter = 0
        self.__callbacks = {}

        self.ourChannel = self.allocateChannel()

        self.doTable: Dict[int, 'DistributedObjectAI'] = {}
        self.zoneTable: Dict[int, set] = {}
        self.parentTable: Dict[int, set] = {}

        self.dcFile = DCFile()
        self.dcFile.read('etc/dclass/otp.dc')
        self.dcFile.read('etc/dclass/cars.dc')

        self.currentSender = None
        self.loop = None
        self.net_thread = None
        self.hoods = None
        self.suitPlanners = {}

        self.zoneDataStore = AIZoneData.AIZoneDataStore()

        self.vismap: Dict[int, Tuple[int]] = {}

        self.connected = Event()

        self.mongoInterface = MongoInterface(self)
        self.doLiveUpdates = True

        self.eventSocket = None # Socket for EventLogger, if enabled.

        self.setEventLogHost('127.0.0.1', port = 46668)

    def run(self):
        self.net_thread = Thread(target=self.__event_loop)
        self.net_thread.start()
        self.connected.wait()
        self.createObjects()

    def _on_net_except(self, loop, context):
        print('Error on networking thread: %s' % context['message'])
        self.loop.stop()
        simbase.stop()

    def __event_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.set_exception_handler(self._on_net_except)
        self.loop.run_until_complete(self.loop.create_connection(self._onConnect, '127.0.0.1', 46668))
        self.loop.run_forever()

    def _onConnect(self):
        self.connection = AIProtocol(self)
        return self.connection

    def readUntilEmpty(self, task):
        while True:
            try:
                dg = self.queue.get(timeout=0.05)
            except queue.Empty:
                break
            else:
                self.handleDatagram(dg)

        return task.cont

    def handleDatagram(self, dg):
        dgi = DatagramIterator(dg)

        recipientCount = dgi.getUint8()
        recipients = [dgi.getInt64() for _ in range(recipientCount)]
        self.currentSender = dgi.getInt64()
        msg_type = dgi.get_uint16()

        if msg_type == STATESERVER_OBJECT_ENTER_AI_RECV:
            if self.currentSender == self.ourChannel:
                return
            self.handleObjEntry(dgi)
        elif msg_type == STATESERVER_OBJECT_DELETE_RAM:
            self.handleObjExit(dgi)
        elif msg_type == STATESERVER_OBJECT_LEAVING_AI_INTEREST:
            pass
        elif msg_type == STATESERVER_OBJECT_CHANGE_ZONE:
            self.handleChangeZone(dgi)
        elif msg_type == STATESERVER_OBJECT_UPDATE_FIELD:
            if self.currentSender == self.ourChannel:
                return
            self.handleUpdateField(dgi)
        elif msg_type == DBSERVER_GET_ESTATE_RESP:
            self.estateMgr.handleGetEstateResp(dgi)
        else:
            print('Unhandled msg type: ', msg_type)

    def handleChangeZone(self, dgi):
        doId = dgi.getUint32()
        newParent = dgi.getUint32()
        newZone = dgi.getUint32()

        # Should we only change location if the old location matches?
        oldParent = dgi.getUint32()
        oldZone = dgi.getUint32()

        self.doTable[doId].location = (newParent, newZone)
        self.storeLocation(doId, oldParent, oldZone, newParent, newZone)

    def storeLocation(self, doId, oldParent, oldZone, newParent, newZone):
        if not doId:
            return

        obj = self.doTable.get(doId)
        oldParentObj = self.doTable.get(oldParent)
        newParentObj = self.doTable.get(newParent)

        if oldParent != newParent and oldParentObj:
            oldParentObj.handleChildLeave(obj, oldZone)

        if oldParent and oldParent in self.parentTable and doId in self.parentTable[oldParent]:
            self.parentTable[oldParent].remove(doId)

        if oldZone != newZone and oldParentObj:
            oldParentObj.handleChildLeaveZone(obj, oldZone)

        if oldZone and oldZone in self.zoneTable and doId in self.zoneTable[oldZone]:
            self.zoneTable[oldZone].remove(doId)

        if newZone:
            self.zoneTable.setdefault(newZone, set())
            self.zoneTable[newZone].add(doId)

        if newParent:
            self.parentTable.setdefault(newParent, set())
            self.parentTable[newParent].add(doId)

        if newParent != oldParent and newParentObj:
            newParentObj.handleChildArrive(obj, newZone)

        if newZone != oldZone and newParentObj:
            newParentObj.handleChildArriveZone(obj, newZone)

    def sendLocation(self, doId, old_parent: int, old_zone: int, new_parent: int, new_zone: int):
        dg = Datagram()
        addServerHeader(dg, [doId], self.ourChannel, STATESERVER_OBJECT_SET_ZONE)
        dg.addUint32(new_parent)
        dg.addUint32(new_zone)
        dg.addUint32(old_parent)
        dg.addUint32(old_zone)
        self.send(dg)

    @staticmethod
    def isClientChannel(channel):
        return config['ClientAgent.MIN_CHANNEL'] <= channel <= config['ClientAgent.MAX_CHANNEL']

    def setInterest(self, clientChannel, handle, context, parentId, zones):
        dg = Datagram()
        addServerHeader(dg, [clientChannel], self.ourChannel, CLIENT_AGENT_SET_INTEREST)
        dg.addUint16(handle)
        dg.addUint32(context)
        dg.addUint32(parentId)
        for zone in zones:
            dg.addUint32(zone)
        self.send(dg)

    def removeInterest(self, clientChannel, handle, context):
        dg = Datagram()
        addServerHeader(dg, [clientChannel], self.ourChannel, CLIENT_AGENT_REMOVE_INTEREST)
        dg.addUint16(handle)
        dg.addUint32(context)
        self.send(dg)

    def handleUpdateField(self, dgi):
        doId = dgi.getUint32()
        fieldNumber = dgi.getUint16()

        # TODO: security check here for client senders.

        field = self.dcFile.getFieldByIndex(fieldNumber)

        self.currentSender = self.currentSender
        do = self.doTable[doId]

        unpacker = DCPacker()
        unpacker.setUnpackData(dgi.getRemainingBytes())

        unpacker.beginUnpack(field)

        try:
            field.receiveUpdate(unpacker, do)
            unpacker.endUnpack()
        except Exception as e:
            print(f'failed to handle field update: <{field.getName()}> from {self.currentAvatarSender}')
            import traceback
            traceback.print_exc()
            print('datagram:', dgi.getRemainingBytes())

            avatarId = self.currentAvatarSender

            if avatarId > 100000000:
                self.ejectPlayer(avatarId, 1, 'Internal server error.')

    @property
    def currentAvatarSender(self):
        return getAvatarIDFromChannel(self.currentSender)

    def ejectPlayer(self, avatarId, bootCode, message):
        dg = Datagram()
        addServerHeader(dg, [getPuppetChannel(avatarId)], self.ourChannel, CLIENT_AGENT_EJECT)
        dg.addUint16(bootCode)
        dg.addString(message)
        self.send(dg)

    @property
    def currentAccountSender(self):
        return getAccountIDFromChannel(self.currentSender)

    def handleObjEntry(self, dgi):
        doId = dgi.getUint32()
        parentId = dgi.getUint32()
        zoneId = dgi.getUint32()
        dcId = dgi.getUint16()

        dclass = self.dcFile.getClass(dcId)

        if doId in self.doTable:
            # This is a response from a generate by us.
            do = self.doTable[doId]
            do.queueUpdates = False
            while do.updateQueue:
                dg = do.updateQueue.popleft()
                self.send(dg)
            return

        if dclass.getName() in ('DistributedCarPlayer', 'DistributedRaceCar'):
            module = import_module(f'ai.{dclass.getName()[11:].lower()}.{dclass.getName()}AI')
            obj = getattr(module, f'{dclass.getName()}AI')(self)
            # Don't queue updates as this object was generated by the stateserver.
            obj.queueUpdates = False
            obj.doId = doId
            obj.parentId = parentId
            obj.zoneId = zoneId
            dclass.receiveUpdateAllRequired(obj, dgi)
            self.doTable[obj.doId] = obj
            self.storeLocation(doId, 0, 0, parentId, zoneId)
            obj.announceGenerate()
        else:
            print(f'unknown object entry: {dclass.getName()}')

    def handleObjExit(self, dgi):
        doId = dgi.getUint32()

        try:
            do = self.doTable.pop(doId)
        except KeyError:
            print(f'Received delete for unknown object: {doId}!')
            return

        do.delete()

        messenger.send(self.getDeleteDoIdEvent(doId))

    def context(self):
        self.__contextCounter = (self.__contextCounter + 1) & 0xFFFFFFFF
        return self.__contextCounter

    def allocateChannel(self):
        return self.channelAllocator.allocate()

    def deallocateChannel(self, channel):
        self.channelAllocator.free(channel)

    def registerForChannel(self, channel):
        if channel in self._registedChannels:
            return
        self._registedChannels.add(channel)

        dg = Datagram()
        addServerControlHeader(dg, CONTROL_SET_CHANNEL)
        dg.addUint64(channel)
        self.send(dg)

    def unregisterForChannel(self, channel):
        if channel not in self._registedChannels:
            return
        self._registedChannels.remove(channel)

        dg = Datagram()
        addServerControlHeader(dg, CONTROL_REMOVE_CHANNEL)
        dg.addUint64(channel)
        self.send(dg)

    def send(self, dg):
        self.connection.sendDatagram(dg)

    def generateWithRequired(self, do, parentId, zoneId, optional = ()):
        doId = self.allocateChannel()
        self.generateWithRequiredAndId(do, doId, parentId, zoneId, optional)

    def generateWithRequiredAndId(self, do, doId, parentId, zoneId, optional = ()):
        do.doId = doId
        self.doTable[doId] = do
        dg = do.dclass.aiFormatGenerate(do, doId, parentId, zoneId, STATESERVERS_CHANNEL, self.ourChannel, optional)
        self.send(dg)

        do.location = (parentId, zoneId)
        do.generate()
        do.announceGenerate()

    def createObjects(self):
        self.registerForChannel(self.ourChannel)

        from .Objects import CarsDistrictAI, ShardManagerUD, HolidayManagerUD

        self.district = CarsDistrictAI(self)
        self.district.name = 'Kachow!'
        self.generateWithRequired(self.district, OTP_DO_ID_FAIRIES, OTP_ZONE_ID_DISTRICTS)

        postRemove = Datagram()
        addServerControlHeader(postRemove, CONTROL_ADD_POST_REMOVE)
        addServerHeader(postRemove, [STATESERVERS_CHANNEL], self.ourChannel, STATESERVER_SHARD_REST)
        postRemove.addUint64(self.ourChannel)
        self.send(postRemove)

        dg = Datagram()
        addServerHeader(dg, [STATESERVERS_CHANNEL], self.ourChannel, STATESERVER_ADD_AI_RECV)
        dg.addUint32(self.district.doId)
        dg.addUint64(self.ourChannel)
        self.send(dg)

        self.shardManager = ShardManagerUD(self)
        self.shardManager.generateGlobalObject(OTP_ZONE_ID_ELEMENTS)

        self.holidayManager = HolidayManagerUD(self)
        self.holidayManager.generateGlobalObject(OTP_ZONE_ID_ELEMENTS)

        self.district.b_setAvailable(True)

    def requestDelete(self, do):
        dg = Datagram()
        addServerHeader(dg, [do.doId], self.ourChannel, STATESERVER_OBJECT_DELETE_RAM)
        dg.addUint32(do.doId)
        self.send(dg)

    @staticmethod
    def getDeleteDoIdEvent(doId):
        return f'do-deleted-{doId}'

    def allocateZone(self):
        return self.zoneAllocator.allocate()

    def deallocateZone(self, zone):
        self.zoneAllocator.free(zone)

    def getAvatarDisconnectReason(self, avId):
        return self.timeManager.disconnectCodes.get(avId)

    def incrementPopulation(self):
        self.stats.b_setAvatarCount(self.stats.getAvatarCount() + 1)

    def decrementPopulation(self):
        self.stats.b_setAvatarCount(self.stats.getAvatarCount() - 1)

    def setEventLogHost(self, host, port = 6668):
        '''
        Set the target host for Event Logger messaging. This should be pointed
        at the UDP IP:port that hosts the cluster's running Event Logger.

        Providing a value of None or an empty string for 'host' will disable
        event logging.
        '''

        if not host:
            self.eventSocket = None
            return

        address = SocketAddress()

        if not address.setHost(host, port):
            self.notify.warning(f'Invalid Event Log host specified: {host}:{post}')
            self.eventSocket = None
        else:
            self.eventSocket = SocketUDPOutgoing()
            self.eventSocket.InitToAddress(address)

    def writeServerEvent(self, event, doId, message):
        '''
        Sends the indicated event data to the event server via UDP for
        recording and/or statistics gathering.
        '''

        if self.eventSocket is None:
            return

        eventDg = PyDatagram()
        eventDg.addUint32(int(time.time()))
        eventDg.addString(event)
        eventDg.addString(str(doId))
        eventDg.addString(message)

        dg = PyDatagram()
        dg.addUint16(eventDg.getLength())
        dg.appendData(eventDg.getMessage())
        self.eventSocket.Send(dg.getMessage())