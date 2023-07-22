from otp import config

import asyncio

from otp.messagedirector import DownstreamMessageDirector, MDUpstreamProtocol
from otp.messagetypes import *
from otp.constants import *
from otp.util import addServerHeader
from .exceptions import *

from panda3d.direct import DCPacker
import json

class DBServerProtocol(MDUpstreamProtocol):
    def handleDatagram(self, dg, dgi):
        sender = dgi.getInt64()
        msgId = dgi.getUint16()

        if msgId == DBSERVER_CREATE_STORED_OBJECT:
            self.handleCreateObject(sender, dgi)
        elif msgId == DBSERVER_DELETE_STORED_OBJECT:
            pass
        elif msgId == DBSERVER_GET_STORED_VALUES:
            self.handleGetStoredValues(sender, dgi)
        elif msgId == DBSERVER_SET_STORED_VALUES:
            self.handleSetStoredValues(sender, dgi)
        elif msgId == DBSERVER_AUTH_REQUEST:
            self.handleAuthRequest(sender, dgi)

    def handleAuthRequest(self, sender, dgi):
        playToken = dgi.getString()

        self.service.loop.create_task(self.service.authRequest(sender, playToken))

    def handleCreateObject(self, sender, dgi):
        context = dgi.getUint32()

        dclassId = dgi.getUint16()
        dclass = self.service.dc.getClass(dclassId)

        coro = None

        if dclass.getName() == 'DistributedCarPlayer':
            dislId = dgi.getUint32()
            fieldCount = dgi.getUint16()

            fields = []

            unpacker = DCPacker()
            unpacker.setUnpackData(dgi.getRemainingBytes())

            for i in range(fieldCount):
                fieldNum = unpacker.rawUnpackUint16()

                f = self.service.dc.getFieldByIndex(fieldNum)

                unpacker.beginUnpack(f)

                fieldArgs = f.unpackArgs(unpacker)
                unpacker.endUnpack()

                fields.append((f.getName(), fieldArgs))

            coro = self.service.createAvatar(sender, context, dclass, dislId, fields)
        else:
            print(f'Unhandled creation for dclass {dclass.getName()}')
            return

        self.service.loop.create_task(coro)

    def handleGetStoredValues(self, sender, dgi):
        context = dgi.getUint32()
        doId = dgi.getUint32()

        fields = []

        while dgi.getRemainingBytes():
            fieldNum = dgi.getUint16()
            field = self.service.dc.getFieldByIndex(fieldNum)
            fields.append(field)

        self.service.loop.create_task(self.service.getStoredValues(sender, context, doId, fields))

    def handleSetStoredValues(self, sender, dgi):
        doId = dgi.getUint32()
        fieldCount = dgi.getUint16()
        fields = []

        unpacker = DCPacker()
        unpacker.setUnpackData(dgi.getRemainingBytes())

        for i in range(fieldCount):
            f = self.service.dc.getFieldByIndex(unpacker.rawUnpackUint16())

            unpacker.beginUnpack(f)

            fieldArgs = f.unpackArgs(unpacker)
            unpacker.endUnpack()

            fields.append((f.getName(), fieldArgs))

        self.service.loop.create_task(self.service.setStoredValues(doId, fields))

from panda3d.direct import DCFile
from otp.dbbackend import SQLBackend, MongoBackend, OTPCreateFailed
from otp.util import getPuppetChannel
from panda3d.core import Datagram, DatagramIterator

class DBServer(DownstreamMessageDirector):
    upstreamProtocol = DBServerProtocol

    minChannel = config['DatabaseServer.MinRange']
    maxChannel = config['DatabaseServer.MaxRange']

    def __init__(self, loop):
        DownstreamMessageDirector.__init__(self, loop)

        self.pool = None

        self.dc = DCFile()
        self.dc.read('etc/dclass/otp.dc')
        self.dc.read('etc/dclass/cars.dc')

        self.wantSQL = config['DatabaseServer.SQL']

        self.backend = SQLBackend(self) if self.wantSQL else MongoBackend(self)

        self.operations = {}

    async def run(self):
        await self.backend.setup()
        await self.connect(config['MessageDirector.HOST'], config['MessageDirector.PORT'])
        await self.route()

    async def createObject(self, sender, context, dclass, fields):
        try:
            doId = await self.backend.createObject(dclass, fields)
        except OTPCreateFailed as e:
            print('creation failed', e)
            doId = 0

        dg = Datagram()
        addServerHeader(dg, [sender], DBSERVERS_CHANNEL, DBSERVER_CREATE_STORED_OBJECT_RESP)
        dg.addUint32(context)
        dg.addUint8(doId == 0)
        dg.addUint32(doId)
        self.sendDatagram(dg)

    async def createObjectNoResponse(self, dclass, accountId, fields) -> int:
        try:
            doId = await self.backend.createObject(dclass, fields)
        except OTPCreateFailed as e:
            print('creation failed', e)
            doId = 0

        return doId

    async def getStoredValues(self, sender, context, doId, fields):
        try:
            fieldDict = await self.backend.queryObjectFields(doId, [field.getName() for field in fields])
        except OTPQueryNotFound:
            fieldDict = None

        self.log.debug(f'Received query request from {sender} with context {context} for doId: {doId}.')

        fieldDg = Datagram()

        dg = Datagram()
        addServerHeader(dg, [sender], DBSERVERS_CHANNEL, DBSERVER_GET_STORED_VALUES_RESP)
        dg.addUint32(context)
        dg.addUint32(doId)

        if fieldDict is None:
            print('object not found... %s' % doId, sender, context)
            self.sendDatagram(dg)
            return

        counter = 0
        packer = DCPacker()

        for field in fields:
            if field.getName() not in fieldDict:
                continue
            if fieldDict[field.getName()] is None:
                continue
            fieldDg.addUint16(field.getNumber())

            fieldValue = fieldDict[field.getName()]

            if self.wantSQL:
               dcName = await self.backend.queryDC(await self.backend.pool.acquire(), doId)
            else:
               dcName = await self.backend.queryDC(doId)

            # Pack the field data.
            field = self.dc.getClassByName(dcName).getFieldByName(field.getName())

            packer = DCPacker()
            packer.beginPack(field)
            field.packArgs(packer, fieldValue)
            packer.endPack()

            fieldDg.addBlob(packer.getBytes())

            counter += 1

        dg.addUint16(counter)

        fieldDi = DatagramIterator(fieldDg)
        dg.appendData(fieldDi.getRemainingBytes())

        self.sendDatagram(dg)

    async def setStoredValues(self, doId, fields):
        self.log.debug(f'Setting stored values for {doId}: {fields}')
        await self.backend.setFields(doId, fields)

    def on_upstream_connect(self):
        self.subscribeChannel(self._client, DBSERVERS_CHANNEL)

    async def authRequest(self, sender: int, playToken: str):
        accountData = await self.backend.queryAccount(playToken)
        accountId = accountData['_id']

        if accountData['avatarId'] == 0:
            carPlayer = self.dc.getClassByName('DistributedCarPlayer') # DistributedCarPuppet

            packer = DCPacker()

            fields = []

            # Iterate through all of the fields.
            fieldCount = carPlayer.getNumInheritedFields()

            for i in range(fieldCount):
                field = carPlayer.getInheritedField(i)

                # Skip the field if it is molecular.
                if field.asMolecularField() is not None:
                    continue

                # Check if the field is db.
                if not field.isDb():
                    continue

                # Check if the user set a value for this field already.
                name = field.getName()

                if name in fields:
                    continue

                # Get the default value of the field.
                default = field.getDefaultValue()
                packer.setUnpackData(default)
                packer.beginUnpack(field)
                value = field.unpackArgs(packer)
                packer.endUnpack()

                fields.append((name, value))

            avatarId = await self.createObjectNoResponse(carPlayer, accountId, fields)

            await self.backend.setField(avatarId, 'setDISLid', (accountId,))

            await self.backend.setField(accountId, 'avatarId', avatarId, 'accounts')

            self.backend.webMongo.cars.update_one(
                {'ownerAccount': accountData['playToken']},
                {'$set': {'dislId': accountId}}
            )

            self.backend.webMongo.cars.update_one(
                {'ownerAccount': accountData['playToken']},
                {'$set': {'playerId': avatarId}}
            )

            accountData['avatarId'] = avatarId

        if accountData['racecarId'] == 0:
            raceCar = self.dc.getClassByName('DistributedRaceCar')

            packer = DCPacker()

            fields = []

            # Iterate through all of the fields.
            fieldCount = raceCar.getNumInheritedFields()

            for i in range(fieldCount):
                field = raceCar.getInheritedField(i)

                # Skip the field if it is molecular.
                if field.asMolecularField() is not None:
                    continue

                # Check if the field is ownrecv.
                if not field.isOwnrecv():
                    continue

                # Check if the user set a value for this field already.
                name = field.getName()

                if name in fields:
                    continue

                # Get the default value of the field.
                default = field.getDefaultValue()
                packer.setUnpackData(default)
                packer.beginUnpack(field)
                value = field.unpackArgs(packer)
                packer.endUnpack()

                fields.append((name, value))

            racecarId = await self.createObjectNoResponse(raceCar, accountId, fields)
            await self.backend.setField(accountId, 'racecarId', racecarId, 'accounts')

            accountData['racecarId'] = racecarId

            self.backend.webMongo.cars.update_one(
                {'ownerAccount': accountData['playToken']},
                {'$set': {'racecarId': racecarId}}
            )

            # Set our DNA on both our avatar and race car
            dna = await self.backend.queryDNA(playToken)

            await self.backend.setField(accountData['avatarId'], 'setDNA', (dna,))
            await self.backend.setField(racecarId, 'setDNA', (dna,))

        if accountData['playerStatusId'] == 0:
            playerStatus = self.dc.getClassByName('CarPlayerStatus')

            fields = []
            fields.append(('setLocationType', [0]))
            fields.append(('setPrivacySettings', [0]))

            playerStatusId = await self.createObjectNoResponse(playerStatus, accountId, fields)
            await self.backend.setField(accountId, 'playerStatusId', playerStatusId, 'accounts')

            accountData['playerStatusId'] = playerStatusId

        # Prepare our response.
        dg = Datagram()
        addServerHeader(dg, [sender], DBSERVERS_CHANNEL, DBSERVER_AUTH_REQUEST_RESP)
        dg.addString(json.dumps(accountData))

        # Send the response to the CA.
        self.sendDatagram(dg)

async def main():
    loop = asyncio.get_running_loop()
    dbServer = DBServer(loop)
    await dbServer.run()

if __name__ == '__main__':
    asyncio.run(main())
