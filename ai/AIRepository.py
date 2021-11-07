from otp.messagetypes import *
from panda3d.core import Datagram, DatagramIterator
from otp.constants import *
from otp.zone import *
from otp.util import *

from panda3d.core import UniqueIdAllocator
from direct.showbase.MessengerGlobal import *
from panda3d.direct import DCFile, DCPacker
import queue

from typing import Dict, Tuple

from otp.networking import ToontownProtocol

from dna.objects import DNAVisGroup
from threading import Thread, Event

import asyncio

from . import AIZoneData

from ai.globals.HoodGlobals import DynamicZonesBegin, DynamicZonesEnd
from .MongoInterface import MongoInterface

from importlib import import_module

class AIProtocol(ToontownProtocol):
    def connection_made(self, transport):
        ToontownProtocol.connection_made(self, transport)
        self.service.connected.set()

    def connection_lost(self, exc):
        raise Exception('AI CONNECTION LOST', exc)

    def receive_datagram(self, dg):
        self.service.queue.put_nowait(dg)

    def send_datagram(self, data: Datagram):
        loop = self.service.loop
        loop.call_soon_threadsafe(self.outgoing_q.put_nowait, data.getMessage())

class AIRepository:
    def __init__(self):
        self.connection = None
        self.queue = queue.Queue()

        base_channel = 4000000

        max_channels = 1000000
        self.minChannel = base_channel
        self.maxChannel = base_channel + max_channels
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
        self.dcFile.read('etc/dclass/toon.dc')

        self.currentSender = None
        self.loop = None
        self.net_thread = None
        self.hoods = None

        self.zoneDataStore = AIZoneData.AIZoneDataStore()

        self.vismap: Dict[int, Tuple[int]] = {}

        self.connected = Event()

        self.mongoInterface = MongoInterface(self)
        self.doLiveUpdates = True

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
        self.loop.run_until_complete(self.loop.create_connection(self._on_connect, '127.0.0.1', 46668))
        self.loop.run_forever()

    def _on_connect(self):
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

        recipientCount = dgi.get_uint8()
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
        do_id = dgi.getUint32()
        new_parent = dgi.getUint32()
        new_zone = dgi.getUint32()

        # Should we only change location if the old location matches?
        old_parent = dgi.getUint32()
        old_zone = dgi.getUint32()

        self.doTable[do_id].location = (new_parent, new_zone)
        self.storeLocation(do_id, old_parent, old_zone, new_parent, new_zone)

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
        addServerHeader(dg, clientChannel, self.ourChannel, CLIENT_AGENT_SET_INTEREST)
        dg.addUint16(handle)
        dg.addUint32(context)
        dg.addUint32(parent_id)
        for zone in zones:
            dg.addUint32(zone)
        self.send(dg)

    def removeInterest(self, clientChannel, handle, context):
        dg = Datagram()
        addServerHeader(dg, clientChannel, self.ourChannel, CLIENT_AGENT_REMOVE_INTEREST)
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

        try:
            do.dclass.receiveUpdate(do, dgi)
        except Exception as e:
            print(f'failed to handle field update: <{field.getName()}> from {self.currentAvatarSender}')
            import traceback
            traceback.print_exc()
            print('datagram:', dgi.getRemainingBytes())

    @property
    def currentAvatarSender(self):
        return getAvatarIDFromChannel(self.currentSender)

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

        if dclass.getName() in ('DistributedToon', 'DistributedEstate', 'DistributedHouse'):
            module = import_module(f'ai.{dclass.getName()[11:].lower()}.{dclass.getName()}AI')
            obj = getattr(module, f'{dclass.getName()}AI')(self)
            # Don't queue updates as this object was generated by the stateserver.
            obj.queueUpdates = False
            obj.do_id = doId
            obj.parentId = parentId
            obj.zoneId = zoneId
            dclass.receiveUpdateAllRequired(obj, dgi)
            self.doTable[obj.do_id] = obj
            self.storeLocation(doId, 0, 0, parentId, zoneId)
            obj.announceGenerate()
        else:
            print('unknown object entry: %s' % dclass.name)

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
        self.connection.send_datagram(dg)

    def generateWithRequired(self, do, parentId, zoneId, optional = ()):
        doId = self.allocateChannel()
        self.generateWithRequiredAndId(do, doId, parentId, zoneId, optional)

    def generateWithRequiredAndId(self, do, doId, parentId, zoneId, optional = ()):
        do.do_id = doId
        self.doTable[doId] = do
        dg = do.dclass.aiFormatGenerate(do, doId, parentId, zoneId, STATESERVERS_CHANNEL, self.ourChannel, optional)
        self.send(dg)

        do.location = (parentId, zoneId)
        do.generate()
        do.announceGenerate()

    def createObjects(self):
        self.registerForChannel(self.ourChannel)

        from .Objects import ToontownDistrictAI, ToontownDistrictStatsAI, DistributedInGameNewsMgrAI, NewsManagerAI, FriendManagerAI
        from .Objects import FishManager, ToontownMagicWordManagerAI, TTCodeRedemptionMgrAI, SafeZoneManagerAI
        from ai.estate.EstateManagerAI import EstateManagerAI
        from .TimeManagerAI import TimeManagerAI
        from ai.quest.QuestManagerAI import QuestManagerAI
        from ai.catalog.CatalogManagerAI import CatalogManagerAI
        from .Objects import DistributedDeliveryManagerAI

        self.district = ToontownDistrictAI(self)
        self.district.name = 'Sillyville'
        self.generateWithRequired(self.district, OTP_DO_ID_TOONTOWN, OTP_ZONE_ID_DISTRICTS)

        postRemove = Datagram()
        addServerControlHeader(postRemove, CONTROL_ADD_POST_REMOVE)
        addServerHeader(postRemove, [STATESERVERS_CHANNEL], self.ourChannel, STATESERVER_SHARD_REST)
        postRemove.addUint64(self.ourChannel)
        self.send(postRemove)

        dg = Datagram()
        addServerHeader(dg, [STATESERVERS_CHANNEL], self.ourChannel, STATESERVER_ADD_AI_RECV)
        dg.addUint32(self.district.do_id)
        dg.addUint64(self.ourChannel)
        self.send(dg)

        self.stats = ToontownDistrictStatsAI(self)
        self.stats.settoontownDistrictId(self.district.do_id)
        self.generateWithRequired(self.stats, OTP_DO_ID_TOONTOWN, OTP_ZONE_ID_DISTRICTS_STATS)

        dg = Datagram()
        addServerHeader(dg, [STATESERVERS_CHANNEL], self.ourChannel, STATESERVER_ADD_AI_RECV)
        dg.addUint32(self.stats.do_id)
        dg.addUint64(self.ourChannel)
        self.send(dg)

        self.timeManager = TimeManagerAI(self)
        self.timeManager.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        self.ingameNewsMgr = DistributedInGameNewsMgrAI(self)
        self.ingameNewsMgr.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        self.newsManager = NewsManagerAI(self)
        self.newsManager.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        self.friendManager = FriendManagerAI(self)
        self.friendManager.generateGlobalObject(OTP_ZONE_ID_MANAGEMENT)

        self.fishManager = FishManager()

        self.magicWordMgr = ToontownMagicWordManagerAI(self)
        self.magicWordMgr.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        self.estateMgr = EstateManagerAI(self)
        self.estateMgr.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        self.codeRedemptionMgr = TTCodeRedemptionMgrAI(self)
        self.codeRedemptionMgr.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        self.safeZoneManager = SafeZoneManagerAI(self)
        self.safeZoneManager.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        self.questManager = QuestManagerAI(self)

        self.catalogManager = CatalogManagerAI(self)
        self.catalogManager.generateWithRequired(OTP_ZONE_ID_MANAGEMENT)

        self.deliveryManager = DistributedDeliveryManagerAI(self)
        self.deliveryManager.generateGlobalObject(OTP_ZONE_ID_MANAGEMENT)

        self.loadZones()

        self.district.b_setAvailable(True)

    def loadZones(self):
        from ai.hood.HoodDataAI import DDHoodAI, TTHoodAI, BRHoodAI, MMHoodAI, DGHoodAI, DLHoodAI, SBHQHoodAI, CBHQHoodAI, LBHQHoodAI, BBHQHoodAI

        self.hoods = [
            DDHoodAI(self),
            TTHoodAI(self),
            BRHoodAI(self),
            MMHoodAI(self),
            DGHoodAI(self),
            DLHoodAI(self),
            SBHQHoodAI(self, None), # TODO: facility mgrs
            CBHQHoodAI(self, None),
            LBHQHoodAI(self, None),
            BBHQHoodAI(self, None)
        ]

        for hood in self.hoods:
            print(f'{hood.__class__.__name__} starting up...')
            hood.startup()

        print('All zones loaded.')

    def requestDelete(self, do):
        dg = Datagram()
        addServerHeader(dg, [do.do_id], self.ourChannel, STATESERVER_OBJECT_DELETE_RAM)
        dg.addUint32(do.do_id)
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