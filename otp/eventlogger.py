from panda3d.core import Datagram, DatagramIterator
from .networking import Service

from datetime import datetime

import socket, asyncio, os

class EventLogger(Service):
    PORT = 46668

    def __init__(self, loop):
        Service.__init__(self)

        # EventLogger sock and clients
        self.sock = None
        self.clients = []

        self.logFolder = 'logs/events/'
        self.logFile = None

        self.createLog()

    def run(self):
        # EventLogger sock and clients
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('127.0.0.1', self.PORT))

        self.log.debug(f'EventLogger listening on port {self.PORT}.')

        while True:
            data, address = self.sock.recvfrom(1024)
            self.handleMessage(data)

    def createLog(self):
        logSuffix = datetime.now().strftime('%m-%d-%Y')

        if not os.path.exists(self.logFolder):
            os.makedirs(self.logFolder)

        self.logFile = self.logFolder + f'event-logger-{logSuffix}.txt'

    def handleMessage(self, data):
        dg = Datagram(data)
        dgi = DatagramIterator(dg)

        bufferLength = dgi.getUint16()

        buffer = dgi.extractBytes(bufferLength)

        _dg = Datagram(buffer)
        _dgi = DatagramIterator(_dg)

        ts = _dgi.getUint32()
        category = _dgi.getString()
        severity = _dgi.getString()
        message = _dgi.getString()

        messageTime = datetime.utcfromtimestamp(ts).strftime('%m/%d/%Y %I:%M %p')

        formatted = f'({messageTime} | {category} | {severity}): {message}\n'

        with open(self.logFile, 'a') as f:
            f.write(formatted)
            f.close()

async def main():
    loop = asyncio.get_running_loop()
    service = EventLogger(loop)
    await service.run()

if __name__ == '__main__':
    asyncio.run(main(), debug = True)