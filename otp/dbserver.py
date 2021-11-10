from otp import config

import asyncio

import datetime

from otp.networking import ChannelAllocator
from otp.messagedirector import DownstreamMessageDirector, MDUpstreamProtocol
from otp.messagetypes import *
from otp.constants import *
from otp.util import addServerHeader
from .exceptions import *

from panda3d.direct import DCPacker

class EstateInfo:
    estateId: int
    parentId: int
    estateZone: int
    houseIds = list

class DBServerProtocol(MDUpstreamProtocol):
    def handle_datagram(self, dg, dgi):
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
        elif msgId == DBSERVER_GET_ESTATE:
            self.handleGetEstate(sender, dgi)
        elif msgId == DBSERVER_UNLOAD_ESTATE:
            self.handleUnloadEstate(dgi)
        elif msgId in (DBSERVER_GET_AVATAR_DETAILS, DBSERVER_GET_PET_DETAILS):
            self.handleGetObjectDetails(dgi)
        elif DBSERVER_ACCOUNT_QUERY:
            self.handle_account_query(sender, dgi)

    def handleGetEstate(self, sender, dgi):
        context = dgi.get_uint32()
        avId = dgi.get_uint32()
        parentId = dgi.get_uint32()
        zoneId = dgi.get_uint32()

        self.service.loop.create_task(self.service.queryEstate(sender, context, avId, parentId, zoneId))

    def handleUnloadEstate(self, dgi):
        avId = dgi.get_uint32()
        parentId = dgi.get_uint32()

        self.service.loop.create_task(self.service.unloadEstate(avId, parentId))

    def handleCreateObject(self, sender, dgi):
        context = dgi.getUint32()

        dclassId = dgi.getUint16()
        dclass = self.service.dc.getClass(dclassId)

        coro = None

        if dclass.getName() == 'DistributedToon':
            dislId = dgi.getUint32()
            pos = dgi.getUint8()
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

            coro = self.service.createToon(sender, context, dclass, dislId, pos, fields)
        else:
            print('Unhandled creation for dclass %s' % dclass.name)
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
        doId = dgi.get_uint32()
        fieldCount = dgi.get_uint16()
        fields = []

        unpacker = DCPacker()

        for i in range(fieldCount):
            f = self.service.dc.getFieldByIndex(dgi.getUint16())

            unpacker.setUnpackData(dgi.getRemainingBytes())

            unpacker.beginUnpack(f)
            fieldArgs = f.unpackArgs(unpacker)
            unpacker.endUnpack()

            fields.append((f.getName(), fieldArgs))

        self.service.loop.create_task(self.service.set_stored_values(doId, fields))

    def handle_account_query(self, sender, dgi):
        do_id = dgi.get_uint32()
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
    upstream_protocol = DBServerProtocol

    minChannel = config['DatabaseServer.MinRange']
    maxChannel = config['DatabaseServer.MaxRange']

    def __init__(self, loop):
        DownstreamMessageDirector.__init__(self, loop)

        self.pool = None

        self.dc = DCFile()
        self.dc.read('etc/dclass/toon.dc')

        self.wantSQL = config['DatabaseServer.SQL']

        if self.wantSQL:
            self.backend = SQLBackend(self)
        else:
            self.backend = MongoBackend(self)

        self.operations = {}

        # Avatar ID to Estate information.
        self.estates: Dict[int] = {}

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
        self.send_datagram(dg)

    async def unloadEstate(self, avId, parentId):
        if avId in self.estates:
            info = self.estates[avId]
            del self.estates[avId]

            # Delete the estate object.
            await self.deleteDO(info.estateId)

            # Delete each house in the list.
            for doId in info.houseIds:
                await self.deleteDO(doId)

    async def queryEstate(self, sender, context, avId, parentId, zoneId):
        toon = await self.backend.query_object_fields(avId, ['setDISLid'], 'DistributedToon')
        accountId = toon['setDISLid'][0]

        account = await self.backend.query_object_fields(accountId, ['ESTATE_ID', 'HOUSE_ID_SET', 'ACCOUNT_AV_SET'], 'Account')

        houseIds = account['HOUSE_ID_SET']
        avatars = account['ACCOUNT_AV_SET']
        estateId = account['ESTATE_ID']

        estateClass = self.dc.getClassByName('DistributedEstate')
        houseClass = self.dc.getClassByName('DistributedHouse')

        # These Fields are REQUIRED but not stored in db.
        estateOther = [
            (estateClass['setDawnTime'], (0,)),
            (estateClass['setClouds'], (0,)),
        ]

        if estateId == 0:
            defaultFields = [
                ('setEstateType', [0]),
                ('setDecorData', [[]]),
                ('setLastEpochTimeStamp', [0]),
                ('setRentalTimeStamp', [0]),
                ('setRentalType', [0]),
                ('setSlot0Items', [[]]),
                ('setSlot1Items', [[]]),
                ('setSlot2Items', [[]]),
                ('setSlot3Items', [[]]),
                ('setSlot4Items', [[]]),
                ('setSlot5Items', [[]]),
                ('setSlot0ToonId', [avatars[0]]),
                ('setSlot1ToonId', [avatars[1]]),
                ('setSlot2ToonId', [avatars[2]]),
                ('setSlot3ToonId', [avatars[3]]),
                ('setSlot4ToonId', [avatars[4]]),
                ('setSlot5ToonId', [avatars[5]])
            ]

            estateId = await self.backend.createObject(estateClass, defaultFields)
            await self.backend.set_field(accountId, 'ESTATE_ID', estateId, 'Account')

        # Generate the estate.
        await self.activateObjectWithOther(estateId, parentId, zoneId, estateClass, estateOther)

        for index, houseId in enumerate(houseIds):
            avatarId = avatars[index]

            # These Fields are REQUIRED but not stored in db.
            houseOther = [
                (houseClass['setHousePos'], (index,)),
                (houseClass['setCannonEnabled'], (0,)),
            ]

            houseDefaults = [
                ('setHouseType', [0]),
                ('setGardenPos', [index]),
                ('setAvatarId', [avatarId]),
                ('setName', ['']),
                ('setColor', [index]),
                ('setAtticItems', ['']),
                ('setInteriorItems', ['']),
                ('setAtticWallpaper', ['']),
                ('setInteriorWallpaper', ['']),
                ('setAtticWindows', ['']),
                ('setInteriorWindows', ['']),
                ('setDeletedItems', [''])
            ]

            if houseId == 0:
                # Create a house.
                houseId = await self.backend.createObject(houseClass, houseDefaults)
                houseIds[index] = houseId

            if avatarId != 0:
                # Update the toon with their new house.
                await self.backend.set_field(avatarId, 'setHouseId', [houseId], 'DistributedToon')

                # Update the house with the toon's name & avatarId.
                owner = await self.backend.query_object_fields(avatarId, ['setName'], 'DistributedToon')
                toonName = owner['setName'][0]

                await self.backend.set_field(houseId, 'setName', [toonName], 'DistributedHouse')
                await self.backend.set_field(houseId, 'setAvatarId', [avatarId], 'DistributedHouse')

            # Generate the houses.
            await self.activateObjectWithOther(houseId, parentId, zoneId, houseClass, houseOther)

        # Update the account's house list.
        await self.backend.set_field(accountId, 'HOUSE_ID_SET', houseIds, 'Account')

        # Make a class containing estate data.
        info = EstateInfo()
        info.estateId = estateId
        info.parentId = parentId
        info.estateZone = zoneId
        info.houseIds = houseIds

        # Map this avatar to their estate info.
        self.estates[avId] = info

        # Let the AI know that we are done.
        dg = Datagram()
        addServerHeader(dg, [sender], DBSERVERS_CHANNEL, DBSERVER_GET_ESTATE_RESP)
        dg.addUint32(context)
        self.send_datagram(dg)

    async def activateObjectWithOther(self, doId: int, parentId: int, zoneId: int, dclass, other: list):
        dg = Datagram()
        addServerHeader(dg, [STATESERVERS_CHANNEL], DBSERVERS_CHANNEL, STATESERVER_OBJECT_CREATE_WITH_REQUIR_OTHER_CONTEXT)
        dg.addUint32(doId)
        dg.addUint32(parentId)
        dg.addUint32(zoneId)
        dg.addUint64(DBSERVERS_CHANNEL)
        dg.addUint16(dclass.number)
        dg.addUint16(len(other))

        for f, arg in other:
            dg.addUint16(f.number)
            f.pack_value(dg, arg)

        self.send_datagram(dg)

    async def deleteDO(self, doId: int):
        dg = Datagram()
        addServerHeader(dg, [doId], DBSERVERS_CHANNEL, STATESERVER_OBJECT_DELETE_RAM)
        dg.addUint32(doId)
        self.send_datagram(dg)

    async def createToon(self, sender, context, dclass, dislId, pos, fields):
        try:
            doId = await self.backend.createObject(dclass, fields)
            account = await self.backend.query_object_fields(dislId, ['ACCOUNT_AV_SET'], 'Account')
            avSet = account['ACCOUNT_AV_SET']
            avSet[pos] = doId
            await self.backend.set_field(dislId, 'ACCOUNT_AV_SET', avSet, 'Account')
        except OTPCreateFailed as e:
            print('creation failed', e)
            doId = 0

        dg = Datagram()
        addServerHeader(dg, [sender], DBSERVERS_CHANNEL, DBSERVER_CREATE_STORED_OBJECT_RESP)
        dg.addUint32(context)
        dg.addUint8(doId == 0)
        dg.addUint32(doId)
        self.send_datagram(dg)

    async def get_stored_values(self, sender, context, doId, fields):
        try:
            fieldDict = await self.backend.query_object_fields(doId, [field.getName() for field in fields])
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
            self.send_datagram(dg)
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

        self.send_datagram(dg)

    async def set_stored_values(self, do_id, fields):
        self.log.debug(f'Setting stored values for {do_id}: {fields}')
        await self.backend.set_fields(do_id, fields)

    def on_upstream_connect(self):
        self.subscribe_channel(self._client, DBSERVERS_CHANNEL)

    async def handleClearWishName(self, avatarId, actionFlag):
        # Grab the fields from the avatar.
        toonFields = await self.backend.query_object_fields(avatarId, ['WishName'], 'DistributedToon')

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
        await self.set_stored_values(avatarId, fields)

    async def queryFriends(self, avatarId):
        fields = await self.backend.query_object_fields(avatarId, ['setFriendsList'], 'DistributedToon')
        friendsList = fields['setFriendsList'][0]

        dg = Datagram()
        addServerHeader(dg, [getPuppetChannel(avatarId)], DBSERVERS_CHANNEL, CLIENT_GET_FRIEND_LIST_RESP)
        dg.addUint8(0) # errorCode

        count = 0
        friendData = {}

        for i in range(0, len(friendsList)):
            friendId = friendsList[i][0]

            friend = await self.backend.query_object_fields(friendId, ['setName', 'setDNAString', 'setPetId'], 'DistributedToon')
            friendData[count] = [friendId, friend['setName'][0], friend['setDNAString'][0], friend['setPetId'][0]]
            count += 1

        dg.addUint16(count)

        for i in friendData:
            friend = friendData[i]

            dg.add_uint32(friend[0]) # friendId
            dg.add_string16(friend[1].encode()) # setName
            dg.add_string16(friend[2]) # setDNAString
            dg.add_uint32(friend[3]) # setPetId

        # Send the response to the client.
        self.send_datagram(dg)

    async def queryObject(self, sender, doId):
        if self.wantSQL:
            await self.backend.queryDC(await self.backend.pool.acquire(), doId)
        else:
            dcName = await self.backend.queryDC(doId)

        if dcName in ['DistributedEstate', 'DistributedHouse', 'DistributedToon']:
            # TODO
            return

        dclass = self.dc.getClassByName('Account')
        toonDC = self.dc.getClassByName('DistributedToon')
        fieldDict = await self.backend.query_object_all(doId, dclass.getName())

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
            toonFields = await self.backend.query_object_fields(avId, ['setName', 'WishNameState', 'WishName', 'setDNAString'], 'DistributedToon')

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

        self.send_datagram(dg)

    async def queryObjectDetails(self, avatarId: int, doId: int, access: int, dcName: str):
        fieldDict = await self.backend.query_object_all(doId, dcName)
        dclass = self.dc.getClassByName(dcName)

        if dcName == 'DistributedToon':
            # These are necessary too.
            fieldDict['setAccess'] = [access]
            fieldDict['setAsGM'] = [False]
            fieldDict['setBattleId'] = [0]

        # Prepare our response.
        dg = Datagram()
        addServerHeader(dg, [getPuppetChannel(avatarId)], DBSERVERS_CHANNEL, CLIENT_GET_AVATAR_DETAILS_RESP)
        dg.add_uint32(doId)
        dg.add_uint8(0)

        # Pack our field data to go to the client.
        for fieldIndex in range(self.dclass.getNumInheritedFields()):
            field = self.dclass.getInheritedField(fieldIndex)
            if not field.isRequired() or field.asMolecularField():
                continue

            packer = DCPacker()
            packer.setUnpackData(dg)

            packer.beginPack(field)
            field.packArgs(packer, fieldDict[field.getName()])

            packer.endPack()

        # Send the response to the client.
        self.send_datagram(dg)

async def main():
    loop = asyncio.get_running_loop()
    db_server = DBServer(loop)
    await db_server.run()

if __name__ == '__main__':
    asyncio.run(main())