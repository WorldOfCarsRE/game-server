from otp import config
import asyncio

from panda3d.direct import DCFile
from panda3d.core import Datagram

from otp.messagedirector import DownstreamMessageDirector, MDUpstreamProtocol, UpstreamServer
from otp.networking import ChannelAllocator
from .clientprotocol import ClientProtocol

class ClientAgentProtocol(MDUpstreamProtocol):
    def handle_datagram(self, dg, dgi):
        sender = dgi.getUint64()
        msgtype = dgi.getUint16()

        print('unhandled', msgtype)

class ClientAgent(DownstreamMessageDirector, UpstreamServer, ChannelAllocator):
    downstream_protocol = ClientProtocol
    upstreamProtocol = ClientAgentProtocol

    minChannel = config['ClientAgent.minChannel']
    maxChannel = config['ClientAgent.maxChannel']

    def __init__(self, loop):
        DownstreamMessageDirector.__init__(self, loop)
        UpstreamServer.__init__(self, loop)
        ChannelAllocator.__init__(self)

        self.dcFile = DCFile()
        self.dcFile.read('etc/dclass/toon.dc')

        self.dcHash = self.dcFile.getHash()

        self.avatarsField = self.dcFile.getClassByName('Account').getFieldByName('ACCOUNT_AV_SET')

        self.loop.set_exception_handler(self._on_exception)

        self._context = 0

        self.log.debug(f'DC Hash is {self.dcHash}')

        self.name_parts = {}
        self.name_categories = {}

        with open('etc/assets/NameMasterEnglish.txt', 'r') as f:
            for line in f:
                if line[0] == '#':
                    continue

                if line.endswith('\r\n'):
                    line = line[:-2]
                elif line.endswith('\n'):
                    line = line[:-1]

                index, category, name = line.split('*')
                index, category = int(index), int(category)
                self.name_parts[index] = name
                self.name_categories[index] = category

        self.listen_task = None
        self.version = config['ClientAgent.Version']

    def _on_exception(self, loop, context):
        print('err', context)

    async def run(self):
        await self.connect(config['MessageDirector.HOST'], config['MessageDirector.PORT'])
        self.listen_task = self.loop.create_task(self.listen(config['ClientAgent.HOST'], config['ClientAgent.PORT'], config['ClientAgent.SSL']))
        await self.route()

    def on_upstream_connect(self):
        pass

    def context(self):
        self._context = (self._context + 1) & 0xFFFFFFFF
        return self._context

async def main():
    loop = asyncio.get_running_loop()
    service = ClientAgent(loop)
    await service.run()

if __name__ == '__main__':
    asyncio.run(main(), debug = True)