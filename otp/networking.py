from asyncio import Queue
from panda3d.core import Datagram

from asyncio import Future
from typing import List

import logging, coloredlogs, traceback, asyncio, struct, ssl

class Service:
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)
        coloredlogs.install(level = 'DEBUG', logger = self.log)
        fh = logging.FileHandler('logs/' + self.__class__.__name__ + '.log')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('(%(name)s::%(asctime)s): %(message)s')
        fh.setFormatter(formatter)
        # add the handler to the logger
        self.log.addHandler(fh)

    async def run(self):
        raise NotImplementedError

    def addParticipant(self, participant):
        raise NotImplementedError

    def subscribeChannel(self, participant, channel):
        raise NotImplementedError

    def unsubscribeChannel(self, participant, channel):
        raise NotImplementedError

class UpstreamServer:
    sslContext = None
    downstreamProtocol = None

    def __init__(self, loop):
        self.loop = loop
        self._server = None
        self._clients = set()

    async def listen(self, host: str, port: int, secure: int = 0):
        if self.downstreamProtocol is None:
            raise Exception('PROTOCOL NOT DEFINED!')

        self.log.debug(f'Listening on {host}:{port}')

        if secure and port == 6667:
            self.sslContext = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.sslContext.load_cert_chain('etc/server.cert', 'etc/server.key')

        self._server = await self.loop.create_server(self.new_client, host, port, ssl=self.sslContext,
                                                     start_serving=False)

        async with self._server:
            await self._server.serve_forever()
            self._clients.clear()

    def new_client(self):
        client = self.downstreamProtocol(self)
        self._clients.add(client)
        return client

class DownstreamClient:
    CLIENT_SSL_CONTEXT = None
    upstreamProtocol = None

    def __init__(self, loop):
        self.loop = loop
        self._client = None

    async def connect(self, host: str, port: int):
        await self.loop.create_connection(self.onConnect, host, port)

    def onConnect(self):
        self._client = self.upstreamProtocol(self)
        return self._client

class DatagramFuture(Future):
    def __init__(self, loop, msgId, sender = None, context = None):
        Future.__init__(self, loop = loop)

        self.futureMsgId = msgId
        self.futureSender = sender
        self.context = context

class ToontownProtocol(asyncio.Protocol):
    def __init__(self, service):
        asyncio.Protocol.__init__(self)
        self.service = service
        self.expected = 0
        self.buf = bytearray()
        self.transport = None
        self.outgoingQ = Queue()
        self.incomingQ = Queue()
        self.tasks: List[asyncio.Task] = []
        self.futures: List[DatagramFuture] = []

    def connection_made(self, transport):
        # name = transport.get_extra_info('peername')
        self.transport = transport
        self.tasks.append(self.service.loop.create_task(self.handleDatagrams()))
        self.tasks.append(self.service.loop.create_task(self.transportDatagrams()))

    def connection_lost(self, exc):
        for task in self.tasks:
            task.cancel()

    def data_received(self, data: bytes):
        self.buf.extend(data)

    def send_datagram(self, data: Datagram):
        self.outgoingQ.put_nowait(data.getMessage())

    async def transportDatagrams(self):
        while True:
            data: bytes = await self.outgoingQ.get()
            self.transport.write(len(data).to_bytes(2, byteorder = 'little'))
            self.transport.write(data)

    async def handleDatagrams(self):
        # TODO: run this tight loop in a seperate process, maybe proccess pool for CA and MD
        expected = 0

        while True:
            if expected:
                if len(self.buf) < expected:
                    await asyncio.sleep(0.01)
                    continue
                else:
                    try:
                        dg = Datagram()
                        dg.appendData(bytes(self.buf[:expected]))
                        self.receiveDatagram(dg)
                        del self.buf[:expected]
                        expected = 0
                        continue
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        continue
            elif len(self.buf) > 2:
                expected = struct.unpack('H', self.buf[:2])[0]
                del self.buf[:2]
                continue
            else:
                await asyncio.sleep(0.01)

    def receiveDatagram(self, data: bytes):
        raise NotImplementedError

    def check_futures(self, dgi, msgId, sender):
        for f in self.futures[:]:
            if msgId != f.futureMsgId:
                continue

            if f.futureSender is not None and sender != f.futureSender:
                continue

            f.set_result((sender, dgi))
            self.futures.remove(f)

class MDParticipant:
    def __init__(self, service: Service):
        self.channels = set()
        self.service = service
        self.service.addParticipant(self)

    def subscribeChannel(self, channel):
        self.service.subscribeChannel(self, channel)

    def unsubscribeChannel(self, channel):
        self.service.unsubscribeChannel(self, channel)

class ChannelAllocator:
    minChannel = None
    maxChannel = None

    def __init__(self):
        self._usedChannels = set()
        self._freedChannels = set()
        self._nextChannel = self.minChannel

    def newChannelId(self):
        channel = self._nextChannel
        self._nextChannel += 1

        if channel in self._usedChannels:
            if self._nextChannel > self.maxChannel:
                if len(self._usedChannels) >= self.maxChannel - self.minChannel:
                    raise OverflowError
                self._nextChannel = self.minChannel
            return self.newChannelId()
        else:
            self._usedChannels.add(channel)
            return channel

    def freeChannelId(self, channel):
        self._freedChannels.add(channel)