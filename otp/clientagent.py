from otp import config, secretsData
import asyncio, builtins

from panda3d.direct import DCFile

from otp.messagedirector import DownstreamMessageDirector, MDUpstreamProtocol, UpstreamServer
from otp.networking import ChannelAllocator
from .clientprotocol import ClientProtocol
from .whitelist import WhiteList

class ClientAgentProtocol(MDUpstreamProtocol):
    def handleDatagram(self, dg, dgi):
        sender = dgi.getUint64()
        msgtype = dgi.getUint16()

        print('unhandled', msgtype)

class ClientAgent(DownstreamMessageDirector, UpstreamServer, ChannelAllocator):
    downstreamProtocol = ClientProtocol
    upstreamProtocol = ClientAgentProtocol

    minChannel = config['ClientAgent.MIN_CHANNEL']
    maxChannel = config['ClientAgent.MAX_CHANNEL']

    def __init__(self, loop):
        DownstreamMessageDirector.__init__(self, loop)
        UpstreamServer.__init__(self, loop)
        ChannelAllocator.__init__(self)

        self.dcFile = DCFile()
        self.dcFile.read('etc/dclass/otp.dc')
        self.dcFile.read('etc/dclass/cars.dc')

        # Doesn't seem dcFile.getHash() matches the client.
        # We'll just hardcode the stock WOC client hashVal.
        # This shouldn't change as we won't be adding new content anyways.
        self.dcHash = 46329213

        self.loop.set_exception_handler(self.onException)

        self._context = 0

        self.log.debug(f'DC Hash is {self.dcHash}')

        self.listen_task = None
        self.version = config['ClientAgent.VERSION']

        self.chatFilter = WhiteList()

        self.encPass = ''
        self.encSalt = ''

        self.useEncryptedTokens = builtins.USE_ENC_TOKENS

        if self.useEncryptedTokens:
            self.log.debug('Using encrypted tokens for authentication.')

            self.encPass = secretsData['Secrets.PASS']
            self.encSalt = secretsData['Secrets.SALT']

    def onException(self, loop, context):
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
