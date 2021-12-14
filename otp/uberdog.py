from otp import config
from otp.messagedirector import DownstreamMessageDirector, MDUpstreamProtocol
from panda3d.direct import DCFile, DCPacker
from otp.constants import *
from otp.messagetypes import *
from otp.util import *
from otp.networking import DatagramFuture
from direct.distributed.PyDatagram import PyDatagram

from panda3d.core import Datagram, DatagramIterator

import asyncio

class UberdogProtocol(MDUpstreamProtocol):
    def __init__(self, service):
        MDUpstreamProtocol.__init__(self, service)

        self.subscribeChannel(self.service.GLOBAL_ID)

    def receiveDatagram(self, dg):
        self.service.log.debug(f'Received datagram: {dg.getMessage()}')
        MDUpstreamProtocol.receiveDatagram(self, dg)

    def handleDatagram(self, dg, dgi):
        sender = dgi.getInt64()
        msgtype = dgi.getUint16()
        self.service.log.debug(f'Got message type {MSG_TO_NAME_DICT[msgtype]} from {sender}.')

        if self.check_futures(dgi, msgtype, sender):
            self.service.log.debug(f'Future handled datagram')
            return

        if msgtype == STATESERVER_OBJECT_UPDATE_FIELD:
            doId = dgi.getUint32()
            if doId != self.service.GLOBAL_ID:
                self.service.log.debug(f'Got field update for unknown object {doId}.')
                return
            self.service.receiveUpdate(sender, dgi)

    def check_futures(self, dgi, msgId, sender):
        pos = dgi.getCurrentIndex()

        for i in range(len(self.futures)):
            future = self.futures[i]
            if future.futureMsgId == msgId and future.futureSender == sender:
                if not future.context:
                    self.futures.remove(future)
                    future.set_result((sender, dgi))
                    return True
                else:
                    context = dgi.getUint32()

                    _dg = Datagram(dgi.getRemainingBytes())
                    _dgi = DatagramIterator(_dg, pos)

                    if future.context == context:
                        self.futures.remove(future)
                        future.set_result((sender, _dgi))
                        return True
        else:
            return False

class Uberdog(DownstreamMessageDirector):
    upstreamProtocol = UberdogProtocol
    GLOBAL_ID = None

    def __init__(self, loop):
        DownstreamMessageDirector.__init__(self, loop)

        self.dclass = dc.getClassByName(self.__class__.__name__[:-2])

        self.lastSender = None

    async def run(self):
        await self.connect(config['MessageDirector.HOST'], config['MessageDirector.PORT'])
        await self.route()

    def on_upstream_connect(self):
        self.subscribeChannel(self._client, self.GLOBAL_ID)
        self.log.debug('Uberdog online')

        dg = self.dclass.aiFormatGenerate(self, self.GLOBAL_ID, OTP_DO_ID_TOONTOWN, OTP_ZONE_ID_MANAGEMENT,
                                            STATESERVERS_CHANNEL, self.GLOBAL_ID, optional_fields=None)
        self.send_datagram(dg)

        dg = PyDatagram()
        addServerControlHeader(dg, CONTROL_ADD_POST_REMOVE)
        addServerHeader(dg, [self.GLOBAL_ID], self.GLOBAL_ID, STATESERVER_OBJECT_DELETE_RAM)
        dg.addUint32(self.GLOBAL_ID)
        self.send_datagram(dg)

    def receiveUpdate(self, sender, dgi):
        self.lastSender = sender
        fieldNumber = dgi.getUint16()
        field = dc.getFieldByIndex(fieldNumber)
        self.log.debug(f'Receiving field update for field {field.getName()} from {sender}.')

        unpacker = DCPacker()
        unpacker.setUnpackData(dgi.getRemainingBytes())

        unpacker.beginUnpack(field)

        field.receiveUpdate(unpacker, self)

        unpacker.endUnpack()

    def register_future(self, msg_type, sender, context):
        f = DatagramFuture(self.loop, msg_type, sender, context)
        self._client.futures.append(f)
        return f

    async def query_location(self, avId, context):
        dg = Datagram()
        addServerHeader(dg, [STATESERVERS_CHANNEL], self.GLOBAL_ID, STATESERVER_OBJECT_LOCATE)
        dg.add_uint32(context)
        dg.add_uint32(avId)
        self.send_datagram(dg)

        f = self.register_future(STATESERVER_OBJECT_LOCATE_RESP, avId, context)

        try:
            sender, dgi = await asyncio.wait_for(f, timeout=10, loop=self.loop)
        except TimeoutError:
            return None, None
        dgi.get_uint32(), dgi.get_uint32()
        success = dgi.get_uint8()
        if not success:
            return None, None
        parent_id, zone_id = dgi.get_uint32(), dgi.get_uint32()

        return parent_id, zone_id

    def sendUpdateToChannel(self, channel, fieldName, args):
        dg = self.dclass.ai_format_update(fieldName, self.GLOBAL_ID, channel, self.GLOBAL_ID, args)
        self.send_datagram(dg)

class CentralLoggerUD(Uberdog):
    GLOBAL_ID = OTP_DO_ID_CENTRAL_LOGGER

    def sendMessage(self, category, event_str, target_disl_id, target_do_id):
        self.log.debug(f'category:{category}, disl_id: {target_disl_id}, do_id: {target_do_id}, event::{event_str}')

CANCELLED = 1
INACTIVE = 0
FRIEND_QUERY = 1
FRIEND_CONSIDERING = 2
NO = 0
YES = 1

class FriendRequest:
    __slots__ = 'avId', 'requestedId', 'state'

    def __init__(self, avId, requestedId, state):
        self.avId = avId
        self.requestedId = requestedId
        self.state = state

    @property
    def cancelled(self):
        return self.state == CANCELLED

class FriendManagerUD(Uberdog):
    GLOBAL_ID = OTP_DO_ID_FRIEND_MANAGER

    def __init__(self, loop):
        Uberdog.__init__(self, loop)
        self._context = 0
        self.requests = {}

    def new_context(self):
        self._context = (self._context + 1) & 0xFFFFFFFF
        return self._context

    def friendQuery(self, requested):
        pass

    def cancelFriendQuery(self, todo0):
        pass

    def inviteeFriendConsidering(self, todo0):
        pass

    def inviteeFriendResponse(self, response, context):
        pass

    def inviteeAcknowledgeCancel(self, todo0):
        pass

    def requestSecret(self):
        pass

    def submitSecret(self, todo0):
        pass

class DistributedDeliveryManagerUD(Uberdog):
    GLOBAL_ID = OTP_DO_ID_TOONTOWN_DELIVERY_MANAGER

    def requestAck(self):
        avId = getAvatarIDFromChannel(self.lastSender)

        if not avId:
            return

        self.sendUpdateToChannel(avId, 'returnAck', [])

async def main():
    import builtins

    builtins.dc = DCFile()
    dc.read('etc/dclass/toon.dc')

    loop = asyncio.get_running_loop()
    centralLogger = CentralLoggerUD(loop)
    friendManager = FriendManagerUD(loop)
    deliveryManager = DistributedDeliveryManagerUD(loop)

    uberdogTasks = [
        asyncio.create_task(centralLogger.run()),
        asyncio.create_task(friendManager.run()),
        asyncio.create_task(deliveryManager.run())
    ]

    await asyncio.gather(*uberdogTasks)

if __name__ == '__main__':
    asyncio.run(main())