from otp import config

import asyncio

import datetime

from otp.networking import ChannelAllocator
from otp.messagedirector import DownstreamMessageDirector, MDUpstreamProtocol
from otp.messagetypes import *
from otp.constants import *
from .exceptions import *

from dc.objects import MolecularField

class DBServerProtocol(MDUpstreamProtocol):
    def handle_datagram(self, dg, dgi):
        sender = dgi.get_channel()
        msg_id = dgi.get_uint16()

        if msg_id == DBSERVER_CREATE_STORED_OBJECT:
            self.handle_create_object(sender, dgi)
        elif msg_id == DBSERVER_DELETE_STORED_OBJECT:
            pass
        elif msg_id == DBSERVER_GET_STORED_VALUES:
            self.handle_get_stored_values(sender, dgi)
        elif msg_id == DBSERVER_SET_STORED_VALUES:
            self.handle_set_stored_values(sender, dgi)
        elif msg_id == DBSERVER_WISHNAME_CLEAR:
            self.handleClearWishName(dgi)
        elif msg_id == DBSERVER_GET_FRIENDS:
            self.handleGetFriends(dgi)
        elif msg_id == DBSERVER_GET_ESTATE:
            self.handleGetEstate(sender, dgi)
        elif DBSERVER_ACCOUNT_QUERY:
            self.handle_account_query(sender, dgi)

    def handleGetEstate(self, sender, dgi):
        context = dgi.get_uint32()
        avId = dgi.get_uint32()
        parentId = dgi.get_uint32()
        zoneId = dgi.get_uint32()

        self.service.loop.create_task(self.service.queryEstate(sender, context, avId, parentId, zoneId))

    def handle_create_object(self, sender, dgi):
        context = dgi.get_uint32()

        dclass_id = dgi.get_uint16()
        dclass = self.service.dc.classes[dclass_id]

        coro = None

        if dclass.name == 'DistributedToon':
            disl_id = dgi.get_uint32()
            pos = dgi.get_uint8()
            field_count = dgi.get_uint16()

            fields = []
            for i in range(field_count):
                f = self.service.dc.fields[dgi.get_uint16()]()
                fields.append((f.name, f.unpack_value(dgi)))

            coro = self.service.create_toon(sender, context, dclass, disl_id, pos, fields)
        else:
            print('Unhandled creation for dclass %s' % dclass.name)
            return

        self.service.loop.create_task(coro)

    def handle_get_stored_values(self, sender, dgi):
        context = dgi.get_uint32()
        do_id = dgi.get_uint32()
        field_count = dgi.get_uint16()
        field_names = [self.service.dc.fields[dgi.get_uint16()]() for _ in range(field_count)]

        self.service.loop.create_task(self.service.get_stored_values(sender, context, do_id, field_names))

    def handle_set_stored_values(self, sender, dgi):
        do_id = dgi.get_uint32()
        field_count = dgi.get_uint16()
        fields = []
        for i in range(field_count):
            f = self.service.dc.fields[dgi.get_uint16()]()
            fields.append((f.name, f.unpack_value(dgi)))

        self.service.loop.create_task(self.service.set_stored_values(do_id, fields))

    def handle_account_query(self, sender, dgi):
        do_id = dgi.get_uint32()
        self.service.loop.create_task(self.service.query_account(sender, do_id))

    def handleClearWishName(self, dgi):
        avatarId = dgi.get_uint32()
        actionFlag = dgi.get_uint8()
        self.service.loop.create_task(self.service.handleClearWishName(avatarId, actionFlag))

    def handleGetFriends(self, dgi):
        avatarId = dgi.get_uint32()
        self.service.loop.create_task(self.service.queryFriends(avatarId))

from dc.parser import parse_dc_file
from otp.dbbackend import MongoBackend, OTPCreateFailed
from otp.util import getPuppetChannel
from dc.util import Datagram

class DBServer(DownstreamMessageDirector):
    upstream_protocol = DBServerProtocol

    min_channel = 100000000
    max_channel = 200000000

    def __init__(self, loop):
        DownstreamMessageDirector.__init__(self, loop)

        self.pool = None

        self.dc = parse_dc_file('etc/dclass/toon.dc')

        self.backend = MongoBackend(self)

        self.operations = {}

    async def run(self):
        await self.backend.setup()
        await self.connect(config['MessageDirector.HOST'], config['MessageDirector.PORT'])
        await self.route()

    async def create_object(self, sender, context, dclass, fields):
        try:
            do_id = await self.backend.create_object(dclass, fields)
        except OTPCreateFailed as e:
            print('creation failed', e)
            do_id = 0

        dg = Datagram()
        dg.add_server_header([sender], DBSERVERS_CHANNEL, DBSERVER_CREATE_STORED_OBJECT_RESP)
        dg.add_uint32(context)
        dg.add_uint8(do_id == 0)
        dg.add_uint32(do_id)
        self.send_datagram(dg)

    async def queryEstate(self, sender, context, avId, parentId, zoneId):
        toon = await self.backend.query_object_fields(avId, ['setDISLid'], 'DistributedToon')
        accountId = toon['setDISLid'][0]

        account = await self.backend.query_object_fields(accountId, ['ESTATE_ID', 'HOUSE_ID_SET', 'ACCOUNT_AV_SET'], 'Account')

        houseIds = account['HOUSE_ID_SET']
        avatars = account['ACCOUNT_AV_SET']
        estateId = account['ESTATE_ID']

        estateClass = self.dc.namespace['DistributedEstate']

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

            estateId = await self.backend.create_object(estateClass, defaultFields)
            await self.backend.set_field(accountId, 'ESTATE_ID', estateId, 'Account')

        # Generate the estate.
        estate = Datagram()
        estate.add_server_header([STATESERVERS_CHANNEL], DBSERVERS_CHANNEL, STATESERVER_OBJECT_CREATE_WITH_REQUIR_OTHER_CONTEXT)
        estate.add_uint32(estateId)
        estate.add_uint32(parentId)
        estate.add_uint32(zoneId)
        estate.add_channel(DBSERVERS_CHANNEL)
        estate.add_uint16(estateClass.number)
        estate.add_uint16(len(estateOther))

        for f, arg in estateOther:
            estate.add_uint16(f.number)
            f.pack_value(estate, arg)

        self.send_datagram(estate)

        dg = Datagram()
        dg.add_server_header([sender], DBSERVERS_CHANNEL, DBSERVER_GET_ESTATE_RESP)
        dg.add_uint32(context)
        self.send_datagram(dg)

    async def create_toon(self, sender, context, dclass, disl_id, pos, fields):
        try:
            do_id = await self.backend.create_object(dclass, fields)
            account = await self.backend.query_object_fields(disl_id, ['ACCOUNT_AV_SET'], 'Account')

            a = Datagram()
            self.dc.namespace['Account']['ACCOUNT_AV_SET'].pack_value(a, account['ACCOUNT_AV_SET'])

            temp = Datagram()
            temp.add_bytes(a.bytes())
            av_set = self.dc.namespace['Account']['ACCOUNT_AV_SET'].unpack_value(temp.iterator())
            print(do_id, disl_id, pos, av_set)
            av_set[pos] = do_id
            temp.seek(0)
            self.dc.namespace['Account']['ACCOUNT_AV_SET'].pack_value(temp, av_set)
            await self.backend.set_field(disl_id, 'ACCOUNT_AV_SET', av_set, 'Account')
        except OTPCreateFailed as e:
            print('creation failed', e)
            do_id = 0

        dg = Datagram()
        dg.add_server_header([sender], DBSERVERS_CHANNEL, DBSERVER_CREATE_STORED_OBJECT_RESP)
        dg.add_uint32(context)
        dg.add_uint8(do_id == 0)
        dg.add_uint32(do_id)
        self.send_datagram(dg)

    async def get_stored_values(self, sender, context, do_id, fields):
        try:
            field_dict = await self.backend.query_object_fields(do_id, [field.name for field in fields])
        except OTPQueryNotFound:
            field_dict = None

        self.log.debug(f'Received query request from {sender} with context {context} for do_id: {do_id}.')

        dg = Datagram()
        dg.add_server_header([sender], DBSERVERS_CHANNEL, DBSERVER_GET_STORED_VALUES_RESP)
        dg.add_uint32(context)
        dg.add_uint32(do_id)
        pos = dg.tell()
        dg.add_uint16(0)

        if field_dict is None:
            print('object not found... %s' % do_id, sender, context)
            self.send_datagram(dg)
            return

        counter = 0
        for field in fields:
            if field.name not in field_dict:
                continue
            if field_dict[field.name] is None:
                continue
            dg.add_uint16(field.number)

            fieldValue = field_dict[field.name]

            dcName = await self.backend._query_dclass(do_id)

            # Pack the field data.
            a = Datagram()
            self.dc.namespace[dcName][field.name].pack_value(a, fieldValue)
            dg.add_bytes(a.bytes())
            counter += 1

        dg.seek(pos)
        dg.add_uint16(counter)
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
        dg.add_server_header([getPuppetChannel(avatarId)], DBSERVERS_CHANNEL, CLIENT_GET_FRIEND_LIST_RESP)
        dg.add_uint8(0) # errorCode

        count = 0
        friendData = {}

        for i in range(0, len(friendsList)):
            friendId = friendsList[i][0]

            friend = await self.backend.query_object_fields(friendId, ['setName', 'setDNAString', 'setPetId'], 'DistributedToon')
            friendData[count] = [friendId, friend['setName'][0], friend['setDNAString'][0], friend['setPetId'][0]]
            count += 1

        dg.add_uint16(count)

        for i in friendData:
            friend = friendData[i]

            dg.add_uint32(friend[0]) # friendId
            dg.add_string16(friend[1].encode()) # setName
            dg.add_string16(friend[2]) # setDNAString
            dg.add_uint32(friend[3]) # setPetId

        # Send the response to the client.
        self.send_datagram(dg)

    async def query_account(self, sender, do_id):
        dclass = self.dc.namespace['Account']
        toon_dclass = self.dc.namespace['DistributedToon']
        fieldDict = await self.backend.query_object_all(do_id, dclass.name)

        temp = Datagram()
        dclass['ACCOUNT_AV_SET'].pack_value(temp, fieldDict['ACCOUNT_AV_SET'])
        avIds = dclass['ACCOUNT_AV_SET'].unpack_value(temp.iterator())

        tempTwo = Datagram()
        dclass['ACCOUNT_AV_SET_DEL'].pack_value(tempTwo, fieldDict['ACCOUNT_AV_SET_DEL'])

        dg = Datagram()
        dg.add_server_header([sender], DBSERVERS_CHANNEL, DBSERVER_ACCOUNT_QUERY_RESP)
        dg.add_bytes(tempTwo.bytes())
        avCount = sum((1 if avId else 0 for avId in avIds))
        self.log.debug(f'Account query for {do_id} from {sender}: {fieldDict}')
        dg.add_uint16(avCount) # Av count
        for avId in avIds:
            if not avId:
                continue
            toonFields = await self.backend.query_object_fields(avId, ['setName', 'WishNameState', 'WishName', 'setDNAString'], 'DistributedToon')

            wishName = toonFields['WishName']

            if wishName:
                wishName = wishName[0].encode()

            nameState = toonFields['WishNameState'][0]

            dg.add_uint32(avId)
            dg.add_string16(toonFields['setName'][0].encode())

            pendingName = b''
            approvedName = b''
            rejectedName = b''

            if nameState == 'APPROVED':
                approvedName = wishName
            elif nameState == 'REJECTED':
                rejectedName = wishName
            else:
                pendingName = wishName

            dg.add_string16(pendingName)
            dg.add_string16(approvedName)
            dg.add_string16(rejectedName)
            dg.add_string16(toonFields['setDNAString'][0])
            dg.add_uint8(avIds.index(avId))
            dg.add_uint8(1 if nameState == 'OPEN' else 0)

        self.send_datagram(dg)

async def main():
    loop = asyncio.get_running_loop()
    db_server = DBServer(loop)
    await db_server.run()

if __name__ == '__main__':
    asyncio.run(main())