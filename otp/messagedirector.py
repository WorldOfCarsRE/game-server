from otp import config
from otp.networking import CarsProtocol, MDParticipant, Service, UpstreamServer, DownstreamClient
from otp.messagetypes import *
from panda3d.core import Datagram, DatagramIterator
from asyncio import Queue
import asyncio
import par

from typing import Dict, Set, List

class MDProtocol(CarsProtocol, MDParticipant):
    def __init__(self, service):
        CarsProtocol.__init__(self, service)
        MDParticipant.__init__(self, service)

        self.postRemoves: List[Datagram] = []

    def connection_made(self, transport):
        CarsProtocol.connection_made(self, transport)

    def connection_lost(self, exc):
        CarsProtocol.connection_lost(self, exc)
        self.service.removeParticipant(self)
        self.postRemove()

    def postRemove(self):
        self.service.log.debug(f'Sending out post removes for participant.')
        while self.postRemoves:
            dg = self.postRemoves.pop(0)
            self.service.q.put_nowait((None, dg))

    def receiveDatagram(self, dg):
        dgi = DatagramIterator(dg)

        recipientCount = dgi.getUint8()
        if recipientCount == 1 and dgi.getInt64() == CONTROL_MESSAGE:
            # Control message.
            msgType = dgi.getUint16()

            if msgType == CONTROL_SET_CHANNEL:
                channel = dgi.getInt64()
                self.subscribeChannel(channel)
            elif msgType == CONTROL_REMOVE_CHANNEL:
                channel = dgi.getInt64()
                self.unsubscribeChannel(channel)
            elif msgType == CONTROL_ADD_RANGE:
                low = dgi.getInt64()
                high = dgi.getInt64()
                for channel in range(low, high, 1):
                    self.channels.add(channel)
            elif msgType == CONTROL_REMOVE_RANGE:
                low = dgi.getInt64()
                high = dgi.getInt64()
                for channel in range(low, high, 1):
                    if channel in self.channels:
                        self.channels.remove(channel)
            elif msgType == CONTROL_ADD_POST_REMOVE:
                postDg = Datagram()
                postDg.appendData(dgi.getRemainingBytes())
                self.service.log.debug(f'Received post remove:{postDg.getMessage()}')
                self.postRemoves.append(postDg)
            elif msgType == CONTROL_CLEAR_POST_REMOVE:
                del self.postRemoves[:]
        else:
            self.service.q.put_nowait((None, dg))

    def handleDatagram(self, dg, dgi):
        self.sendDatagram(dg)

class MessageDirector(Service):
    def __init__(self):
        Service.__init__(self)
        self.participants: Set[MDParticipant] = set()
        self.channelSubscriptions: Dict[int, Set[MDParticipant]] = {}
        self.q = Queue()

    def subscribeChannel(self, participant: MDParticipant, channel: int):
        if channel not in participant.channels:
            participant.channels.add(channel)

        if channel not in self.channelSubscriptions:
            self.channelSubscriptions[channel] = set()

        if participant not in self.channelSubscriptions[channel]:
            self.channelSubscriptions[channel].add(participant)

    def unsubscribeChannel(self, participant: MDParticipant, channel: int):
        if channel in participant.channels:
            participant.channels.remove(channel)

        if channel in self.channelSubscriptions:
            if participant in self.channelSubscriptions[channel]:
                self.channelSubscriptions[channel].remove(participant)

    def unsubscribeAll(self, participant: MDParticipant):
        while participant.channels:
            channel = participant.channels.pop()
            self.unsubscribeChannel(participant, channel)

    def addParticipant(self, participant: MDParticipant):
        self.participants.add(participant)

    def removeParticipant(self, participant: MDParticipant):
        self.unsubscribeAll(participant)
        self.participants.remove(participant)

    def processDatagram(self, participant: MDParticipant, dg: Datagram):
        dgi = DatagramIterator(dg)

        recipientCount = dgi.getUint8()
        recipients = (dgi.getInt64() for _ in range(recipientCount))

        receivingParticipants = {p for c in recipients if c in self.channelSubscriptions for p in self.channelSubscriptions[c]}

        if participant is not None and participant in receivingParticipants:
            receivingParticipants.remove(participant)

        pos = dgi.getCurrentIndex()

        try:
            for participant in receivingParticipants:
                _dgi = DatagramIterator(dg, pos)
                participant.handleDatagram(dg, _dgi)
        except Exception as e:
            self.log.debug(f'Exception while handling datagram: {e.__class__}: {repr(e)}')

    async def route(self):
        while True:
            participant, dg = await self.q.get()
            self.processDatagram(participant, dg)

class MasterMessageDirector(MessageDirector, UpstreamServer):
    downstreamProtocol = MDProtocol

    def __init__(self, loop):
        MessageDirector.__init__(self)
        UpstreamServer.__init__(self, loop)
        self.loop.set_exception_handler(self.onException)

    def onException(self, loop, context):
        print('err', context)

    async def run(self):
        self.loop.create_task(self.route())
        await self.listen(config['MessageDirector.HOST'], config['MessageDirector.PORT'])

class MDUpstreamProtocol(CarsProtocol, MDParticipant):
    def __init__(self, service):
        CarsProtocol.__init__(self, service)
        MDParticipant.__init__(self, service)

    def connection_made(self, transport):
        CarsProtocol.connection_made(self, transport)
        self.service.on_upstream_connect()

    def connection_lost(self, exc):
        CarsProtocol.connection_lost(self, exc)
        raise Exception('lost upsteam connection!', exc)

    def subscribeChannel(self, channel):
        dg = Datagram()
        dg.addUint8(1)
        dg.addUint64(CONTROL_MESSAGE)
        dg.addUint16(CONTROL_SET_CHANNEL)
        dg.addUint64(channel)
        self.sendDatagram(dg)

    def unsubscribeChannel(self, channel):
        dg = Datagram()
        dg.addUint8(1)
        dg.addUint64(CONTROL_MESSAGE)
        dg.addUint16(CONTROL_REMOVE_CHANNEL)
        dg.addUint64(channel)
        self.sendDatagram(dg)

    def receiveDatagram(self, dg):
        self.service.q.put_nowait((None, dg))

    def handleDatagram(self, dg, dgi):
        raise NotImplementedError

class DownstreamMessageDirector(MessageDirector, DownstreamClient):
    upstreamProtocol = MDUpstreamProtocol

    def __init__(self, loop):
        MessageDirector.__init__(self)
        DownstreamClient.__init__(self, loop)

    async def run(self):
        raise NotImplementedError

    def subscribeChannel(self, participant, channel):
        subscribeUpstream = channel not in self.channelSubscriptions or not len(self.channelSubscriptions[channel])
        MessageDirector.subscribeChannel(self, participant, channel)

        if subscribeUpstream:
            self._client.subscribeChannel(channel)

    def unsubscribeChannel(self, participant, channel):
        MessageDirector.unsubscribeChannel(self, participant, channel)

        if len(self.channelSubscriptions[channel]) == 0:
            self._client.unsubscribeChannel(channel)

    def processDatagram(self, participant, dg):
        MessageDirector.processDatagram(self, participant, dg)

        if participant is not None:
            # send upstream
            self._client.sendDatagram(dg)

    def sendDatagram(self, dg: Datagram):
        self._client.sendDatagram(dg)

async def main():
    loop = asyncio.get_running_loop()
    service = MasterMessageDirector(loop)
    await service.run()

if __name__ == '__main__':
    asyncio.run(main())
