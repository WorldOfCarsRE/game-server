from otp import config
from otp.networking import ToontownProtocol, MDParticipant, Service, UpstreamServer, DownstreamClient
from dc.messagetypes import *
from panda3d.core import Datagram, DatagramIterator
from asyncio import Queue
import asyncio
import par

from typing import Dict, Set, List

class MDProtocol(ToontownProtocol, MDParticipant):
    def __init__(self, service):
        ToontownProtocol.__init__(self, service)
        MDParticipant.__init__(self, service)

        self.postRemoves: List[Datagram] = []

    def connection_made(self, transport):
        ToontownProtocol.connection_made(self, transport)

    def connection_lost(self, exc):
        ToontownProtocol.connection_lost(self, exc)
        self.service.remove_participant(self)
        self.post_remove()

    def post_remove(self):
        self.service.log.debug(f'Sending out post removes for participant.')
        while self.postRemoves:
            dg = self.postRemoves.pop(0)
            self.service.q.put_nowait((None, dg))

    def receive_datagram(self, dg):
        dgi = DatagramIterator(dg)

        recipientCount = dgi.getUint8()
        if recipientCount == 1 and dgi.getInt64() == CONTROL_MESSAGE:
            # Control message.
            msgType = dgi.getUint16()

            if msgType == CONTROL_SET_CHANNEL:
                channel = dgi.getInt64()
                self.subscribe_channel(channel)
            elif msgType == CONTROL_REMOVE_CHANNEL:
                channel = dgi.getInt64()
                self.unsubscribe_channel(channel)
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

    def handle_datagram(self, dg, dgi):
        self.send_datagram(dg)

class MessageDirector(Service):
    def __init__(self):
        Service.__init__(self)
        self.participants: Set[MDParticipant] = set()
        self.channel_subscriptions: Dict[int, Set[MDParticipant]] = {}
        self.q = Queue()

    def subscribe_channel(self, participant: MDParticipant, channel: int):
        if channel not in participant.channels:
            participant.channels.add(channel)

        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()

        if participant not in self.channel_subscriptions[channel]:
            self.channel_subscriptions[channel].add(participant)

    def unsubscribe_channel(self, participant: MDParticipant, channel: int):
        if channel in participant.channels:
            participant.channels.remove(channel)

        if channel in self.channel_subscriptions:
            if participant in self.channel_subscriptions[channel]:
                self.channel_subscriptions[channel].remove(participant)

    def unsubscribe_all(self, participant: MDParticipant):
        while participant.channels:
            channel = participant.channels.pop()
            self.unsubscribe_channel(participant, channel)

    def add_participant(self, participant: MDParticipant):
        self.participants.add(participant)

    def remove_participant(self, participant: MDParticipant):
        self.unsubscribe_all(participant)
        self.participants.remove(participant)

    def process_datagram(self, participant: MDParticipant, dg: Datagram):
        dgi = DatagramIterator(dg)

        recipientCount = dgi.getUint8()
        recipients = (dgi.getInt64() for _ in range(recipientCount))

        receivingParticipants = {p for c in recipients if c in self.channel_subscriptions for p in self.channel_subscriptions[c]}

        if participant is not None and participant in receivingParticipants:
            receivingParticipants.remove(participant)

        pos = dgi.getCurrentIndex()

        try:
            for participant in receivingParticipants:
                _dgi = DatagramIterator(dg, pos)
                participant.handle_datagram(dg, _dgi)
        except Exception as e:
            self.log.debug(f'Exception while handling datagram: {e.__class__}: {repr(e)}')

    async def route(self):
        while True:
            participant, dg = await self.q.get()
            self.process_datagram(participant, dg)

class MasterMessageDirector(MessageDirector, UpstreamServer):
    downstream_protocol = MDProtocol

    def __init__(self, loop):
        MessageDirector.__init__(self)
        UpstreamServer.__init__(self, loop)
        self.loop.set_exception_handler(self._on_exception)

    def _on_exception(self, loop, context):
        print('err', context)

    async def run(self):
        self.loop.create_task(self.route())
        await self.listen(config['MessageDirector.HOST'], config['MessageDirector.PORT'])

class MDUpstreamProtocol(ToontownProtocol, MDParticipant):
    def __init__(self, service):
        ToontownProtocol.__init__(self, service)
        MDParticipant.__init__(self, service)

    def connection_made(self, transport):
        ToontownProtocol.connection_made(self, transport)
        self.service.on_upstream_connect()

    def connection_lost(self, exc):
        ToontownProtocol.connection_lost(self, exc)
        raise Exception('lost upsteam connection!', exc)

    def subscribe_channel(self, channel):
        dg = Datagram()
        dg.addUint8(1)
        dg.addUint64(CONTROL_MESSAGE)
        dg.addUint16(CONTROL_SET_CHANNEL)
        dg.addUint64(channel)
        self.send_datagram(dg)

    def unsubscribe_channel(self, channel):
        dg = Datagram()
        dg.addUint8(1)
        dg.addUint64(CONTROL_MESSAGE)
        dg.addUint16(CONTROL_REMOVE_CHANNEL)
        dg.addUint64(channel)
        self.send_datagram(dg)

    def receive_datagram(self, dg):
        self.service.q.put_nowait((None, dg))

    def handle_datagram(self, dg, dgi):
        raise NotImplementedError

class DownstreamMessageDirector(MessageDirector, DownstreamClient):
    upstream_protocol = MDUpstreamProtocol

    def __init__(self, loop):
        MessageDirector.__init__(self)
        DownstreamClient.__init__(self, loop)

    async def run(self):
        raise NotImplementedError

    def subscribe_channel(self, participant, channel):
        subscribe_upstream = channel not in self.channel_subscriptions or not len(self.channel_subscriptions[channel])
        MessageDirector.subscribe_channel(self, participant, channel)

        if subscribe_upstream:
            self._client.subscribe_channel(channel)

    def unsubscribe_channel(self, participant, channel):
        MessageDirector.unsubscribe_channel(self, participant, channel)

        if len(self.channel_subscriptions[channel]) == 0:
            self._client.unsubscribe_channel(channel)

    def process_datagram(self, participant, dg):
        MessageDirector.process_datagram(self, participant, dg)

        if participant is not None:
            # send upstream
            self._client.send_datagram(dg)

    def send_datagram(self, dg: Datagram):
        self._client.send_datagram(dg)

async def main():
    loop = asyncio.get_running_loop()
    service = MasterMessageDirector(loop)
    await service.run()

if __name__ == '__main__':
    asyncio.run(main())
