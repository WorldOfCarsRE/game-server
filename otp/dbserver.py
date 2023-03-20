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
        elif msgId == DBSERVER_WISHNAME_CLEAR:
            self.handleClearWishName(dgi)
        elif msgId == DBSERVER_GET_FRIENDS:
            self.handleGetFriends(dgi)
        elif msgId in (DBSERVER_GET_AVATAR_DETAILS, DBSERVER_GET_PET_DETAILS):
            self.handleGetObjectDetails(dgi)
        elif msgId == DBSERVER_AUTH_REQUEST:
            self.handleAuthRequest(sender, dgi)
        elif DBSERVER_ACCOUNT_QUERY:
            self.handle_account_query(sender, dgi)

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

        self.service.loop.create_task(self.service.get_stored_values(sender, context, doId, fields))

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

    def handle_account_query(self, sender, dgi):
        do_id = dgi.getUint32()
        self.service.loop.create_task(self.service.queryObject(sender, do_id))

    def handleClearWishName(self, dgi):
        avatarId = dgi.getUint32()
        actionFlag = dgi.getUint8()
        self.service.loop.create_task(self.service.handleClearWishName(avatarId, actionFlag))

    def handleGetFriends(self, dgi):
        avatarId = dgi.getUint32()
        self.service.loop.create_task(self.service.queryFriends(avatarId))

    def handleGetObjectDetails(self, dgi):
        avatarId = dgi.getUint32()
        doId = dgi.getUint32()
        access = dgi.getUint8()
        dcName = dgi.getString()
        self.service.loop.create_task(self.service.queryObjectDetails(avatarId, doId, access, dcName))

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

        if self.wantSQL:
            self.backend = SQLBackend(self)
        else:
            self.backend = MongoBackend(self)

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

    async def activateObjectWithOther(self, doId: int, parentId: int, zoneId: int, dclass, other: list):
        dg = Datagram()
        addServerHeader(dg, [STATESERVERS_CHANNEL], DBSERVERS_CHANNEL, STATESERVER_OBJECT_CREATE_WITH_REQUIR_OTHER_CONTEXT)
        dg.addUint32(doId)
        dg.addUint32(parentId)
        dg.addUint32(zoneId)
        dg.addUint64(DBSERVERS_CHANNEL)
        dg.addUint16(dclass.getNumber())
        dg.addUint16(len(other))

        for f, arg in other:
            packer = DCPacker()
            packer.rawPackUint16(f.getNumber())

            packer.beginPack(f)
            f.packArgs(packer, arg)
            packer.endPack()

            dg.appendData(packer.getBytes())

        self.sendDatagram(dg)

    async def deleteDO(self, doId: int):
        dg = Datagram()
        addServerHeader(dg, [doId], DBSERVERS_CHANNEL, STATESERVER_OBJECT_DELETE_RAM)
        dg.addUint32(doId)
        self.sendDatagram(dg)

    async def createAvatar(self, dclass, accountId, fields) -> int:
        try:
            doId = await self.backend.createObject(dclass, fields)
        except OTPCreateFailed as e:
            print('creation failed', e)
            doId = 0

        return doId

    async def get_stored_values(self, sender, context, doId, fields):
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

    async def handleClearWishName(self, avatarId, actionFlag):
        # Grab the fields from the avatar.
        toonFields = await self.backend.queryObjectFields(avatarId, ['WishName'], 'DistributedToon')

        if actionFlag == 1:
            # This name was approved.
            # Set their name.
            fields = [
                ('WishNameState', ('',)),
                ('WishName', ('',)),
                ('setName', (toonFields['WishName'][0],))
            ]
        else:
            # This name was rejected.
            # Set them to the OPEN state so they can try again.
            fields = [
                ('WishNameState', ('OPEN',)),
                ('WishName', ('',))
            ]

        # Set the fields in the database.
        await self.setStoredValues(avatarId, fields)

    async def queryFriends(self, avatarId):
        fields = await self.backend.queryObjectFields(avatarId, ['setFriendsList'], 'DistributedToon')
        friendsList = fields['setFriendsList'][0]

        dg = Datagram()
        addServerHeader(dg, [getPuppetChannel(avatarId)], DBSERVERS_CHANNEL, CLIENT_GET_FRIEND_LIST_RESP)
        dg.addUint8(0) # errorCode

        count = 0
        friendData = {}

        for i in range(0, len(friendsList)):
            friendId = friendsList[i][0]

            friend = await self.backend.queryObjectFields(friendId, ['setName', 'setDNAString', 'setPetId'], 'DistributedToon')
            friendData[count] = [friendId, friend['setName'][0], friend['setDNAString'][0], friend['setPetId'][0]]
            count += 1

        dg.addUint16(count)

        for i in friendData:
            friend = friendData[i]

            dg.addUint32(friend[0]) # friendId
            dg.addString(friend[1]) # setName
            dg.addBlob(friend[2]) # setDNAString
            dg.addUint32(friend[3]) # setPetId

        # Send the response to the client.
        self.sendDatagram(dg)

    async def queryObject(self, sender, doId):
        if self.wantSQL:
            await self.backend.queryDC(await self.backend.pool.acquire(), doId)
        else:
            dcName = await self.backend.queryDC(doId)

        if dcName in ['DistributedCarPlayer']:
            # TODO
            return

        dclass = self.dc.getClassByName('Account')
        toonDC = self.dc.getClassByName('DistributedToon')
        fieldDict = await self.backend.queryObjectAll(doId, dclass.getName())

        avIds = fieldDict['ACCOUNT_AV_SET']

        field = dclass.getFieldByName('ACCOUNT_AV_SET_DEL')

        packer = DCPacker()
        packer.beginPack(field)
        field.packArgs(packer, fieldDict['ACCOUNT_AV_SET_DEL'])
        packer.endPack()

        dg = Datagram()
        addServerHeader(dg, [sender], DBSERVERS_CHANNEL, DBSERVER_ACCOUNT_QUERY_RESP)
        dg.addBlob(packer.getBytes())
        avCount = sum((1 if avId else 0 for avId in avIds))
        self.log.debug(f'Account query for {doId} from {sender}: {fieldDict}')
        dg.addUint16(avCount) # Av count
        for avId in avIds:
            if not avId:
                continue
            toonFields = await self.backend.queryObjectFields(avId, ['setName', 'WishNameState', 'WishName', 'setDNAString'], 'DistributedToon')

            wishName = toonFields['WishName']

            if wishName:
                wishName = wishName[0]

            nameState = toonFields['WishNameState'][0]

            dg.addUint32(avId)
            dg.addString(toonFields['setName'][0])

            pendingName = ''
            approvedName = ''
            rejectedName = ''

            if nameState == 'APPROVED':
                approvedName = wishName
            elif nameState == 'REJECTED':
                rejectedName = wishName
            else:
                pendingName = wishName

            dg.addString(pendingName)
            dg.addString(approvedName)
            dg.addString(rejectedName)
            dg.addBlob(toonFields['setDNAString'][0])
            dg.addUint8(avIds.index(avId))
            dg.addUint8(1 if nameState == 'OPEN' else 0)

        self.sendDatagram(dg)

    async def queryObjectDetails(self, avatarId: int, doId: int, access: int, dcName: str):
        fieldDict = await self.backend.queryObjectAll(doId, dcName)
        dclass = self.dc.getClassByName(dcName)

        if dcName == 'DistributedToon':
            # These are necessary too.
            fieldDict['setAccess'] = [access]
            fieldDict['setAsGM'] = [False]
            fieldDict['setBattleId'] = [0]

        # Prepare our response.
        dg = Datagram()
        addServerHeader(dg, [getPuppetChannel(avatarId)], DBSERVERS_CHANNEL, CLIENT_GET_AVATAR_DETAILS_RESP)
        dg.addUint32(doId)
        dg.addUint8(0)

        # Pack our field data to go to the client.
        packedData = self.packDetails(dclass, fieldDict)
        dg.appendData(packedData)

        # Send the response to the client.
        self.sendDatagram(dg)

    def packDetails(self, dclass, fields):
        # Pack required fields.
        fieldPacker = DCPacker()

        for i in range(dclass.getNumInheritedFields()):
            field = dclass.getInheritedField(i)

            if not field.isRequired() or field.asMolecularField():
                continue

            k = field.getName()
            v = fields.get(k, None)

            fieldPacker.beginPack(field)

            if not v:
                fieldPacker.packDefaultValue()
            else:
                field.packArgs(fieldPacker, v)

            fieldPacker.endPack()

        return fieldPacker.getBytes()

    async def authRequest(self, sender: int, playToken: str):
        accountData = await self.backend.queryAccount(playToken)
        accountId = accountData['_id']

        if accountData['avatarId'] == 0:
            carPlayer = self.dc.getClassByName('DistributedCarPlayer')

            packer = DCPacker()

            fields = []

            # Iterate through all of the fields.
            fieldCount = carPlayer.getNumInheritedFields()

            for i in range(fieldCount):
                field = carPlayer.getInheritedField(i)

                # Skip the field if it is molecular.
                if field.asMolecularField() is not None:
                    continue

                # Check if the field is required.
                if not field.isRequired():
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

            avatarId = await self.createAvatar(carPlayer, accountId, fields)

            await self.backend.setField(avatarId, 'setDISLname', (accountData['playToken'],))
            await self.backend.setField(avatarId, 'setDISLid', (accountId,))
            await self.backend.setField(avatarId, 'setDNA', (await self.backend.queryDNA(playToken),))

            await self.backend.setField(accountId, 'avatarId', avatarId, 'accounts')

            self.backend.webMongo.cars.update_one(
                {'ownerAccount': accountData['playToken']},
                {'$set': {'dislId': accountId}}
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

                # Check if the field is required.
                if not field.isRequired():
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

            racecarId = await self.createAvatar(raceCar, accountId, fields)
            await self.backend.setField(accountId, 'racecarId', racecarId, 'accounts')

            accountData['racecarId'] = racecarId

        if accountData['playerStatusId'] == 0:
            playerStatus = self.dc.getClassByName('CarPlayerStatus')

            fields = []
            fields.append(('setLocationType', [0]))
            fields.append(('setPrivacySettings', [0]))

            playerStatusId = await self.createAvatar(playerStatus, accountId, fields)
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