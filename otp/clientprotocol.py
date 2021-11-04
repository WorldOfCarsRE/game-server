import time
import json
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Union, Dict, Tuple

from Crypto.Cipher import AES
from dataslots import with_slots
from panda3d.direct import DCMolecularField
from panda3d.core import Datagram, DatagramIterator

from otp import config
from otp.messagedirector import MDParticipant
from otp.messagetypes import *
from otp.networking import ToontownProtocol, DatagramFuture
from otp.zone import *
from otp.constants import *
from otp.util import *
from otp.zoneutil import VIS_ZONES, getCanonicalZoneId, getTrueZoneId

class NamePart(IntEnum):
    BOY_TITLE = 0
    GIRL_TITLE = 1
    NEUTRAL_TITLE = 2
    BOY_FIRST = 3
    GIRL_FIRST = 4
    NEUTRAL_FIRST = 5
    CAP_PREFIX = 6
    LAST_PREFIX = 7
    LAST_SUFFIX = 8

@with_slots
@dataclass
class PotentialAvatar:
    doId: int
    name: str
    wish_name: str
    approved_name: str
    rejected_name: str
    dna_string: str
    index: int
    allowName: int

class ClientState(IntEnum):
    NEW = 0
    ANONYMOUS = 1
    AUTHENTICATED = 2
    AVATAR_CHOOSER = 3
    CREATING_AVATAR = 4
    SETTING_AVATAR = 5
    PLAY_GAME = 6

class ClientDisconnect(IntEnum):
    INTERNAL_ERROR = 1
    RELOGGED = 100
    CHAT_ERROR = 120
    LOGIN_ERROR = 122
    OUTDATED_CLIENT = 125
    ADMIN_KICK = 151
    ACCOUNT_SUSPENDED = 152
    SHARD_DISCONNECT = 153
    PERIOD_EXPIRED = 288
    PERIOD_EXPIRED2 = 349
    SERVER_MAINTENANCE = 154

@with_slots
@dataclass
class PendingObject:
    doId: int
    dcId: int
    parentId: int
    zoneId: int
    datagrams: list

class Interest:
    def __init__(self, client, handle, context, parentId, zones):
        self.client = client
        self.handle = handle
        self.context = context
        self.parentId = parentId
        self.zones = zones
        self.done = False
        self.ai = False
        self.pendingObjects: List[int] = []

@with_slots
@dataclass
class ObjectInfo:
    doId: int
    dcId: int
    parentId: int
    zoneId: int

CLIENTAGENT_SECRET = bytes.fromhex(config['General.LOGIN_SECRET'])

@with_slots
@dataclass
class DISLAccount:
    username: str
    dislId: int
    access: str
    accountType: str
    createFriendsWithChat: str
    chatCodeCreationRule: str
    whitelistChatEnabled: str

class ClientProtocol(ToontownProtocol, MDParticipant):
    def __init__(self, service):
        ToontownProtocol.__init__(self, service)
        MDParticipant.__init__(self, service)

        self.state: int = ClientState.NEW
        self.channel: int = service.new_channel_id()
        self.alloc_channel = self.channel
        self.subscribe_channel(self.channel)

        self.interests: List[Interest] = []
        self.visibleObjects: Dict[int, ObjectInfo] = {}
        self.ownedObjects: Dict[int, ObjectInfo] = {}

        # TODO: make this configurable
        self.uberdogs: List[int] = [OTP_DO_ID_FRIEND_MANAGER]

        self.account: Union[DISLAccount, None] = None
        self.avatar_id: int = 0
        self.createdAvId: int = 0
        self.wanted_name: str = ''
        self.potential_avatar = None
        self.potential_avatars: List[PotentialAvatar] = []
        self.avsDeleted: List[Tuple[int, int]] = []
        self.pendingObjects: Dict[int, PendingObject] = {}

    def disconnect(self, booted_index, booted_text):
        for task in self.tasks:
            task.cancel()
        del self.tasks[:]
        resp = Datagram()
        resp.addUint16(CLIENT_GO_GET_LOST)
        resp.addUint16(booted_index)
        resp.add_string16(booted_text.encode('utf-8'))
        self.transport.write(len(resp).to_bytes(2, byteorder='little'))
        self.transport.write(resp.bytes())
        self.transport.close()
        self.service.log.debug(f'Booted client {self.channel} with index {booted_index} and text: "{booted_text}"')

    def connection_lost(self, exc):
        self.service.log.debug(f'Connection lost to client {self.channel}')
        ToontownProtocol.connection_lost(self, exc)

        if self.avatar_id:
            self.delete_avatar_ram()

        self.service.remove_participant(self)

    def connection_made(self, transport):
        ToontownProtocol.connection_made(self, transport)
        self.subscribe_channel(CLIENTS_CHANNEL)

    def delete_avatar_ram(self):
        dg = Datagram()
        dg.add_server_header([self.avatar_id], self.channel, STATESERVER_OBJECT_DELETE_RAM)
        dg.addUint32(self.avatar_id)
        self.service.send_datagram(dg)

    def receive_datagram(self, dg):
        dgi = DatagramIterator(dg)
        msgtype = dgi.get_uint16()

        if msgtype != CLIENT_OBJECT_UPDATE_FIELD:
            self.service.log.debug(f'Got message type {MSG_TO_NAME_DICT[msgtype]} from client {self.channel}')

        if msgtype == CLIENT_HEARTBEAT:
            self.send_datagram(dg)
            return

        if msgtype == CLIENT_DISCONNECT:
            return

        if self.state == ClientState.NEW:
            if msgtype == CLIENT_LOGIN_TOONTOWN:
                self.receive_login(dgi)
                self.state = ClientState.AUTHENTICATED
            else:
                self.service.log.debug(f'Unexpected message type during handshake {msgtype}.')
        elif self.state == ClientState.AUTHENTICATED:
            if msgtype == CLIENT_GET_AVATARS:
                self.receiveGetAvatars(dgi)
            elif msgtype == CLIENT_ADD_INTEREST:
                self.receive_add_interest(dgi)
            elif msgtype == CLIENT_REMOVE_INTEREST:
                self.receive_remove_interest(dgi)
            elif msgtype == CLIENT_OBJECT_UPDATE_FIELD:
                self.receive_update_field(dgi)
            else:
                self.service.log.debug(f'Unexpected message type during post authentication {msgtype}.')
        elif self.state == ClientState.AVATAR_CHOOSER:
            if msgtype == CLIENT_CREATE_AVATAR:
                self.receive_create_avatar(dgi)
            elif msgtype == CLIENT_SET_AVATAR:
                self.receive_set_avatar(dgi)
            elif msgtype == CLIENT_SET_WISHNAME:
                self.receive_set_wishname(dgi)
            elif msgtype == CLIENT_REMOVE_INTEREST:
                self.receive_remove_interest(dgi)
            elif msgtype == CLIENT_OBJECT_UPDATE_FIELD:
                doId = dgi.get_uint32()
                if doId == OTP_DO_ID_CENTRAL_LOGGER:
                    self.receive_update_field(dgi, doId)
                else:
                    self.service.log.debug(f'Unexpected field update for doId {doId} during avatar chooser.')
            elif msgtype == CLIENT_DELETE_AVATAR:
                self.receive_delete_avatar(dgi)
            elif msgtype == CLIENT_SET_WISHNAME_CLEAR:
                self.receiveSetWishNameClear(dgi)
            else:
                self.service.log.debug(f'Unexpected message type during avatar chooser {msgtype}.')
        elif self.state == ClientState.CREATING_AVATAR:
            if msgtype == CLIENT_SET_AVATAR:
                self.receive_set_avatar(dgi)
            elif msgtype == CLIENT_SET_WISHNAME:
                self.receive_set_wishname(dgi)
            elif msgtype == CLIENT_SET_NAME_PATTERN:
                self.receive_set_name_pattern(dgi)
            elif msgtype == CLIENT_OBJECT_UPDATE_FIELD:
                doId = dgi.get_uint32()
                if doId == OTP_DO_ID_CENTRAL_LOGGER:
                    self.receive_update_field(dgi, doId)
                else:
                    self.service.log.debug(f'Unexpected field update for doId {doId} during avatar creation.')
            else:
                self.service.log.debug(f'Unexpected message type during avatar creation {msgtype}.')
        else:
            if msgtype == CLIENT_ADD_INTEREST:
                self.receive_add_interest(dgi)
            elif msgtype == CLIENT_REMOVE_INTEREST:
                self.receive_remove_interest(dgi)
            elif msgtype == CLIENT_GET_FRIEND_LIST:
                self.receive_get_friend_list(dgi)
            elif msgtype == CLIENT_OBJECT_LOCATION:
                self.receive_client_location(dgi)
            elif msgtype == CLIENT_OBJECT_UPDATE_FIELD:
                self.receive_update_field(dgi)
            elif msgtype == CLIENT_SET_AVATAR:
                self.receive_set_avatar(dgi)
            elif msgtype in (CLIENT_GET_AVATAR_DETAILS, CLIENT_GET_PET_DETAILS):
                self.receiveGetObjectDetails(dgi, msgtype)
            else:
                self.service.log.debug(f'Unhandled msg type {msgtype} in state {self.state}')

    def receive_update_field(self, dgi, doId = None):
        if doId is None:
            doId = dgi.get_uint32()

        fieldNumber = dgi.get_uint16()

        field = self.service.dcFile.getFieldByIndex[fieldNumber]()

        sendable = False

        if field.isOwnsend() and doId in self.ownedObjects:
            sendable = True
        elif field.isClsend():
            sendable = True

        if not sendable:
            self.disconnect(ClientDisconnect.INTERNAL_ERROR, 'Tried to send nonsendable field to object.')
            self.service.log.warn(f'Client {self.channel} tried to update {doId} with nonsendable field {field.name}. '
                                  f'DCField keywords: {field.keywords}')
            return

        pos = dgi.getCurrentIndex()
        field.unpack_bytes(dgi)
        dgi.seek(pos)

        resp = Datagram()
        addServerHeader(resp, [doId], self.channel, STATESERVER_OBJECT_UPDATE_FIELD)
        resp.addUint32(doId)
        resp.addUint16(fieldNumber)
        resp.add_bytes(dgi.getRemainingBytes())
        self.service.send_datagram(resp)

        if field.name == 'setTalk':
            # TODO: filtering
            resp = Datagram()
            resp.addUint16(CLIENT_OBJECT_UPDATE_FIELD)
            resp.addUint32(doId)
            resp.addUint16(fieldNumber)
            resp.add_bytes(dgi.getRemainingBytes())
            self.send_datagram(resp)

    def receive_client_location(self, dgi):
        doId = dgi.getUint32()
        parentId = dgi.getUint32()
        zoneId = dgi.getUint32()

        self.service.log.debug(f'Client {self.channel} is setting their location to {parentId} {zoneId}')

        if doId in self.ownedObjects:
            self.ownedObjects[doId].zoneId = zoneId
            self.ownedObjects[doId].parentId = parentId
            dg = Datagram()
            addServerHeader(dg, [doId], self.channel, STATESERVER_OBJECT_SET_ZONE)
            dg.addUint32(parentId)
            dg.addUint32(zoneId)
            self.service.send_datagram(dg)
        else:
            self.service.log.debug(f'Client {self.channel} tried setting location for unowned object {doId}!')

    def receive_get_friend_list(self, dgi):
        self.service.log.debug(f'Friend list query received from {self.channel}')

        # Friend Structure
        # uint32 doId
        # string name
        # string dnaString
        # uint32 petId

        query = Datagram()
        addServerHeader(query, [DBSERVERS_CHANNEL], self.channel, DBSERVER_GET_FRIENDS)
        query.addUint32(self.avatar_id)
        self.service.send_datagram(query)

    def receive_set_avatar(self, dgi):
        av_id = dgi.get_uint32()

        self.service.log.debug(f'client {self.channel} is setting their avatar to {av_id}')

        if not av_id:
            if self.avatar_id:
                # Client is logging out of their avatar.
                self.delete_avatar_ram()
                self.ownedObjects.clear()
                self.visibleObjects.clear()

                self.unsubscribe_channel(getClientSenderChannel(self.account.dislId, self.avatar_id))
                self.unsubscribe_channel(getPuppetChannel(self.avatar_id))
                self.channel = getClientSenderChannel(self.account.dislId, 0)
                self.subscribe_channel(self.channel)

                self.state = ClientState.AUTHENTICATED
                self.avatar_id = 0
                return
            else:
                # Do nothing.
                return
        elif self.state == ClientState.PLAY_GAME:
            self.service.log.debug(f'Client {self.channel} tried to set their avatar {av_id} while avatar is already set to {self.avatar_id}.')
            return

        pot_av = None

        for pa in self.potential_avatars:
            if pa and pa.doId == av_id:
                pot_av = pa
                break

        if pot_av is None:
            self.disconnect(ClientDisconnect.INTERNAL_ERROR, 'Could not find avatar on account.')
            return

        self.avatar_id = av_id
        self.createdAvId = 0

        self.state = ClientState.SETTING_AVATAR

        self.channel = getClientSenderChannel(self.account.dislId, self.avatar_id)
        self.subscribe_channel(self.channel)
        self.subscribe_channel(getPuppetChannel(self.avatar_id))

        dclass = self.service.dcFile.getClassByName('DistributedToon')

        access = 2 if self.account.access == b'FULL' else 1

        # These Fields are REQUIRED but not stored in db.
        other_fields = [
            (dclass['setAccess'], (access,)),
            (dclass['setPreviousAccess'], (access,)),
            (dclass['setAsGM'], (False,)),
            (dclass['setBattleId'], (0,))
        ]

        if pot_av.approved_name:
            other_fields.append((dclass['setName'], (pot_av.approved_name,)))
            pot_av.approved_name = ''

        dg = Datagram()
        addServerHeader(dg, [STATESERVERS_CHANNEL], self.channel, STATESERVER_OBJECT_CREATE_WITH_REQUIR_OTHER_CONTEXT)
        dg.addUint32(av_id)
        dg.addUint32(0)
        dg.addUint32(0)
        dg.addUint64(self.channel)
        dg.addUint16(dclass.number)
        dg.addUint16(len(other_fields))

        for f, arg in other_fields:
            dg.addUint16(f.number)
            f.pack_value(dg, arg)

        self.service.send_datagram(dg)

    def receive_create_avatar(self, dgi):
        _ = dgi.get_uint16()
        dna = dgi.get_blob16()
        pos = dgi.get_uint8()
        self.service.log.debug(f'Client {self.channel} requesting avatar creation with dna {dna} and pos {pos}.')

        if not 0 <= pos < 6 or self.potential_avatars[pos] is not None:
            self.service.log.debug(f'Client {self.channel} tried creating avatar in invalid position.')
            return

        self.potential_avatar = PotentialAvatar(doId = 0, name = 'Toon', wish_name = '', approved_name = '',
                                                      rejected_name = '', dnaString = dna, index = pos, allowName = 1)

        dclass = self.service.dcFile.namespace['DistributedToon']

        dg = Datagram()
        dg.add_server_header([DBSERVERS_CHANNEL], self.channel, DBSERVER_CREATE_STORED_OBJECT)
        dg.addUint32(0)
        dg.addUint16(dclass.number)
        dg.addUint32(self.account.dislId)
        dg.add_uint8(pos)
        pos = dg.getCurrentIndex()
        dg.addUint16(0)

        default_toon = dict(DEFAULT_TOON)
        default_toon['setDNAString'] = (dna,)
        default_toon['setDISLid'] = (self.account.dislId,)
        default_toon['WishName'] = ('',)
        default_toon['WishNameState'] = ('CLOSED',)
        default_toon['setAccountName'] = (self.account.username,)

        count = 0
        for field in dclass.inherited_fields:
            if not isinstance(field, MolecularField) and field.is_db:
                if field.name == 'DcObjectType':
                    continue
                dg.addUint16(field.number)
                field.pack_value(dg, default_toon[field.name])
                count += 1

        dg.seek(pos)
        dg.addUint16(count)

        self.state = ClientState.CREATING_AVATAR

        self.service.send_datagram(dg)

        self.tasks.append(self.service.loop.create_task(self.created_avatar()))

    async def created_avatar(self):
        f = DatagramFuture(self.service.loop, DBSERVER_CREATE_STORED_OBJECT_RESP)
        self.futures.append(f)
        sender, dgi = await f
        context = dgi.get_uint32()
        return_code = dgi.get_uint8()
        av_id = dgi.get_uint32()

        av = self.potential_avatar
        av.doId = av_id
        self.potential_avatars[av.index] = av
        self.potential_avatar = None

        resp = Datagram()
        resp.addUint16(CLIENT_CREATE_AVATAR_RESP)
        resp.addUint16(0) # Context
        resp.add_uint8(return_code)  # Return Code
        resp.addUint32(avId) # avId
        self.send_datagram(resp)

        self.createdAvId = av_id

        self.service.log.debug(f'New avatar {av_id} created for client {self.channel}.')

    def receive_set_wishname(self, dgi):
        av_id = dgi.getUint32()
        name = dgi.getString()

        av = self.get_potential_avatar(av_id)

        self.service.log.debug(f'Received wishname request from {self.channel} for avatar {av_id} for name "{name}".')

        pending = name.encode('utf-8')
        approved = b''
        rejected = b''

        failed = False

        resp = Datagram()
        resp.addUint16(CLIENT_SET_WISHNAME_RESP)
        resp.addUint32(av_id)
        resp.addUint16(failed)
        resp.add_string16(pending)
        resp.add_string16(approved)
        resp.add_string16(rejected)

        self.send_datagram(resp)

        if av_id and av:
            dclass = self.service.dcFile.namespace['DistributedToon']
            wishname_field = dclass['WishName']
            wishname_state_field = dclass['WishNameState']

            resp = Datagram()
            resp.add_server_header([DBSERVERS_CHANNEL], self.channel, DBSERVER_SET_STORED_VALUES)
            resp.addUint32(av_id)
            resp.addUint16(2)
            resp.addUint16(wishname_state_field.number)
            wishname_state_field.pack_value(resp, ('PENDING',))
            resp.addUint16(wishname_field.number)
            wishname_field.pack_value(resp, (name,))
            self.service.send_datagram(resp)

    def receive_set_name_pattern(self, dgi):
        av_id = dgi.get_uint32()

        self.service.log.debug(f'Got name pattern request for av_id {av_id}.')

        title_index, title_flag = dgi.get_int16(), dgi.get_int16()
        first_index, first_flag = dgi.get_int16(), dgi.get_int16()
        last_prefix_index, last_prefix_flag = dgi.get_int16(), dgi.get_int16()
        last_suffix_index, last_suffix_flag = dgi.get_int16(), dgi.get_int16()

        resp = Datagram()
        resp.addUint16(CLIENT_SET_NAME_PATTERN_ANSWER)
        resp.addUint32(av_id)

        if av_id != self.created_av_id:
            resp.add_uint8(1)
            self.send_datagram(resp)
            return

        if first_index <= 0 and last_prefix_index <= 0 and last_suffix_index <= 0:
            self.service.log.debug(f'Received request for empty name for {av_id}.')
            resp.add_uint8(2)
            self.send_datagram(resp)
            return

        if (last_prefix_index <= 0 <= last_suffix_index) or (last_suffix_index <= 0 <= last_prefix_index):
            self.service.log.debug(f'Received request for invalid last name for {av_id}.')
            resp.add_uint8(3)
            self.send_datagram(resp)
            return

        try:
            title = self.get_name_part(title_index, title_flag, {NamePart.BOY_TITLE, NamePart.GIRL_TITLE, NamePart.NEUTRAL_TITLE})
            first = self.get_name_part(first_index, first_flag, {NamePart.BOY_FIRST, NamePart.GIRL_FIRST, NamePart.NEUTRAL_FIRST})
            last_prefix = self.get_name_part(last_prefix_index, last_prefix_flag, {NamePart.CAP_PREFIX, NamePart.LAST_PREFIX})
            last_suffix = self.get_name_part(last_suffix_index, last_suffix_flag, {NamePart.LAST_SUFFIX})
        except KeyError as e:
            resp.add_uint8(4)
            self.send_datagram(resp)
            self.service.log.debug(f'Received invalid index for name part. {e.args}')
            return

        name = f'{title}{" " if title else ""}{first}{" " if first else ""}{last_prefix}{last_suffix}'

        for pot_av in self.potential_avatars:
            if pot_av and pot_av.doId == av_id:
                pot_av.approved_name = name.strip()
                break

        resp.add_uint8(0)
        self.send_datagram(resp)

    def get_name_part(self, index, flag, categories):
        if index >= 0:
            if self.service.name_categories[index] not in categories:
                self.service.log.debug(f'Received invalid index for pattern name: {index}. Expected categories: {categories}')
                return

            title = self.service.name_parts[index]
            return title.capitalize() if flag else title
        else:
            return ''

    def receive_delete_avatar(self, dgi):
        av_id = dgi.get_uint32()

        av = self.get_potential_avatar(av_id)

        if not av:
            return

        self.potential_avatars[av.index] = None
        avatars = [pot_av.doId if pot_av else 0 for pot_av in self.potential_avatars]
        self.avsDeleted.append((av_id, int(time.time())))

        field = self.service.dcFile.namespace['Account']['ACCOUNT_AV_SET']
        del_field = self.service.dcFile.namespace['Account']['ACCOUNT_AV_SET_DEL']

        dg = Datagram()
        dg.add_server_header([DBSERVERS_CHANNEL], self.channel, DBSERVER_SET_STORED_VALUES)
        dg.addUint32(self.account.dislId)
        dg.addUint16(2)
        dg.addUint16(field.number)
        field.pack_value(dg, avatars)
        dg.addUint16(del_field.number)
        del_field.pack_value(dg, self.avsDeleted)
        self.service.send_datagram(dg)

        resp = Datagram()
        resp.addUint16(CLIENT_DELETE_AVATAR_RESP)
        resp.add_uint8(0) # Return code

        av_count = sum((1 if potAv else 0 for potAv in self.potential_avatars))
        resp.addUint16(av_count)

        for potAv in self.potential_avatars:
            if not potAv:
                continue
            resp.addUint32(potAv.doId)
            resp.add_string16(potAv.name.encode('utf-8'))
            resp.add_string16(potAv.wish_name.encode('utf-8'))
            resp.add_string16(potAv.approved_name.encode('utf-8'))
            resp.add_string16(potAv.rejected_name.encode('utf-8'))

            dnaString = potAv.dnaString

            if not isinstance(dnaString, bytes):
                dnaString = dnaString.encode()

            resp.add_string16(dnaString)
            resp.add_uint8(potAv.index)

        self.send_datagram(resp)

    def receive_remove_interest(self, dgi, ai = False):
        handle = dgi.getUint16()

        if dgi.getRemainingSize():
            context = dgi.getUint32()
        else:
            context = None

        interest = None

        for _interest in self.interests:
            if _interest.handle == handle:
                interest = _interest
                break

        if not interest:
            self.service.log.debug(f'Got unexpected interest removal from client {self.channel} for interest handle '
                                   f'{handle} with context {context}')
            return

        self.service.log.debug(f'Got remove interest request from client {self.channel} for interest handle '
                               f'{handle} with context {context}')

        parentId = interest.parentId

        uninterested_zones = []

        for zone in interest.zones:
            if len(self.lookupInterest(parentId, zone)) == 1:
                uninterested_zones.append(zone)

        to_remove = []

        for doId in self.visibleObjects:
            do = self.visibleObjects[doId]
            if do.parentId == parentId and do.zoneId in uninterested_zones:
                self.service.log.debug(f'Object {doId} killed by interest remove.')
                self.sendRemoveObject(doId)

                to_remove.append(doId)

        for doId in to_remove:
            del self.visibleObjects[doId]

        for zone in uninterested_zones:
            self.unsubscribe_channel(location_as_channel(parentId, zone))

        self.interests.remove(interest)

        if not ai:
            resp = Datagram()
            resp.addUint16(CLIENT_DONE_INTEREST_RESP)
            resp.addUint16(handle)
            resp.addUint32(context)
            self.send_datagram(resp)

    def receiveGetAvatars(self, dgi):
        query = Datagram()
        addServerHeader(query, [DBSERVERS_CHANNEL], self.channel, DBSERVER_ACCOUNT_QUERY)

        dislId = self.account.dislId
        query.addUint32(dislId)
        fieldNumber = self.service.avatarsField.getNumber()
        query.addUint16(fieldNumber)
        self.service.send_datagram(query)

        self.tasks.append(self.service.loop.create_task(self.doLogin()))

    async def doLogin(self):
        f = DatagramFuture(self.service.loop, DBSERVER_ACCOUNT_QUERY_RESP)
        self.futures.append(f)
        sender, dgi = await f

        av_del_field = self.service.dcFile.namespace['Account']['ACCOUNT_AV_SET_DEL']
        self.service.log.debug('Begin unpack of deleted avatars.')
        try:
            self.avsDeleted = av_del_field.unpack_value(dgi)
        except Exception:
            import traceback
            traceback.print_exc()
            return
        self.service.log.debug(f'Avatars deleted list for {self.account.username}: {self.avsDeleted}')

        pos = dgi.getCurrentIndex()

        avatar_info = [None] * 6

        for i in range(dgi.get_uint16()):
            potAv = PotentialAvatar(doId = dgi.getUint32(), name = dgi.getString(), wish_name = dgi.getString(),
                                     approved_name = dgi.getString(), rejected_name = dgi.getString(),
                                     dna_string = dgi.getBlob(), index = dgi.getUint8(), allowName = dgi.getUint8())

            avatar_info[potAv.index] = potAv

        self.potential_avatars = avatar_info

        self.state = ClientState.AVATAR_CHOOSER

        resp = Datagram()
        resp.addUint16(CLIENT_GET_AVATARS_RESP)
        dgi.seek(pos)
        resp.add_uint8(0) # Return code
        resp.add_bytes(dgi.remaining_bytes())
        self.send_datagram(resp)

    def receive_login(self, dgi):
        playToken = dgi.getString()
        clientVersion = dgi.getString()
        hashVal = dgi.getUint32()
        wantMagicWords = dgi.getString()

        if clientVersion != self.service.version:
            self.disconnect(ClientDisconnect.OUTDATED_CLIENT, 'Version mismatch')
            return

        self.service.log.debug(f'playToken:{playToken}, clientVersion:{clientVersion}, hashVal:{hashVal}, '
                               f'wantMagicWords:{wantMagicWords}')

        try:
            playToken = bytes.fromhex(playToken)
            nonce, tag, playToken = playToken[:16], playToken[16:32], playToken[32:]
            cipher = AES.new(CLIENTAGENT_SECRET, AES.MODE_EAX, nonce)
            data = cipher.decrypt_and_verify(playToken, tag)
            self.service.log.debug(f'Login token data:{data}')
            data = json.loads(data)
            for key in list(data.keys()):
                value = data[key]
                if type(value) == str:
                    data[key] = value
            self.account = DISLAccount(**data)
        except ValueError as e:
            self.disconnect(ClientDisconnect.LOGIN_ERROR, 'Invalid token')
            return

        self.channel = getClientSenderChannel(self.account.dislId, 0)
        self.subscribe_channel(self.channel)
        self.subscribe_channel(getAccountChannel(self.account.dislId))

        resp = Datagram()
        resp.addUint16(CLIENT_LOGIN_TOONTOWN_RESP)

        returnCode = 0  # -13 == period expired
        resp.add_uint8(returnCode)

        errorString = '' # 'Bad DC Version Compare'
        resp.addString(errorString)

        resp.addUint32(self.account.dislId)
        resp.addString(self.account.username)

        accountNameApproved = True
        resp.addUint8(accountNameApproved)

        resp.addString(self.account.whitelistChatEnabled)
        resp.addString(self.account.createFriendsWithChat)
        resp.addString(self.account.chatCodeCreationRule)

        t = time.time() * 10e6
        usecs = int(t % 10e6)
        secs = int(t / 10e6)
        resp.addUint32(secs)
        resp.addUint32(usecs)

        resp.addString(self.account.access)
        resp.addString(self.account.whitelistChatEnabled)

        lastLoggedIn = time.strftime('%c') # time.strftime('%c')
        resp.addString(lastLoggedIn)

        accountDays = 0
        resp.add_int32(accountDays)

        resp.addString(self.account.accountType)
        resp.addString(self.account.username)

        self.send_datagram(resp)

    def receive_add_interest(self, dgi, ai = False):
        handle = dgi.getUint16()
        contextId = dgi.getUint32()
        parentId = dgi.getUint32()

        numZones = dgi.getRemainingSize() // 4

        zones = []

        for i in range(numZones):
            zoneId = dgi.getUint32()
            if zoneId == 1:
                continue
            zones.append(zoneId)
            if numZones == 1:
                canonicalzoneId = getCanonicalZoneId(zoneId)
                if canonicalzoneId in VIS_ZONES:
                    for viszoneId in VIS_ZONES[canonicalzoneId]:
                        truezoneId = getTruezoneId(viszoneId, zoneId)
                        zones.append(truezoneId)

        self.service.log.debug(f'Client {self.channel} is requesting interest with handle {handle} and context {contextId} '
                               f'for location {parentId} {zones}')

        if self.state <= ClientState.AUTHENTICATED and parentId != OTP_DO_ID_TOONTOWN:
            self.service.log.debug(f'Client {self.channel} requested unexpected interest in state {self.state}. Ignoring.')
            return

        previous_interest = None

        for _interest in self.interests:
            if _interest.handle == handle:
                previous_interest = _interest
                break

        if previous_interest is None:
            interest = Interest(self.channel, handle, contextId, parentId, zones)
            self.interests.append(interest)
        else:
            self.service.log.debug(f'Altering interest {handle} (done: {previous_interest.done}): {previous_interest.zones} -> {zones}')
            self.interests.remove(previous_interest)

            if previous_interest.parentId != parentId:
                killed_zones = previous_interest.zones
            else:
                killed_zones = set(previous_interest.zones).difference(set(zones))

            for _interest in self.interests:
                killed_zones = killed_zones.difference(set(_interest.zones))
                if not killed_zones:
                    break

            self.service.log.debug(f'Zones killed by altering interest: {killed_zones}')

            if killed_zones:
                for doId in list(self.visibleObjects.keys()):
                    obj = self.visibleObjects[doId]
                    if obj.parentId == parentId and obj.zoneId in killed_zones:
                        self.service.log.debug(f'Object {obj.doId}, location ({obj.parentId}, {obj.zoneId}), killed by altered interest: {zones}')
                        self.sendRemoveObject(obj.doId)
                        del self.visibleObjects[doId]

            for zone in killed_zones:
                self.unsubscribe_channel(location_as_channel(previous_interest.parentId, zone))

            interest = Interest(self.channel, handle, contextId, parentId, zones)
            self.interests.append(interest)

            for doId in list(self.pendingObjects.keys()):
                if not self.pendingObjectNeeded(doId):
                    del self.pendingObjects[doId]

        interest.ai = ai

        if not zones:
            interest.done = True
            if not ai:
                resp = Datagram()
                resp.addUint16(CLIENT_DONE_INTEREST_RESP)
                resp.addUint16(handle)
                resp.addUint32(contexId)
                self.send_datagram(resp)
                return

        queryReq = Datagram()
        addServerHeader(queryReq, [parentId], self.channel, STATESERVER_QUERY_ZONE_OBJECT_ALL)
        queryReq.addUint16(handle)
        queryReq.addUint32(contextId)
        queryReq.addUint32(parentId)

        for zone in zones:
            queryReq.addUint32(zone)
            self.subscribe_channel(location_as_channel(parentId, zone))

        self.service.send_datagram(queryReq)

    def handle_datagram(self, dg, dgi):
        pos = dgi.getCurrentIndex()
        sender = dgi.getInt64()

        if sender == self.channel:
            return

        msgtype = dgi.getUint16()

        self.check_futures(dgi, msgtype, sender)

        if msgtype == STATESERVER_OBJECT_ENTERZONE_WITH_REQUIRED_OTHER:
            self.handleObjectEntrance(dgi, sender)
        elif msgtype == STATESERVER_OBJECT_ENTER_OWNER_RECV:
            self.handle_owned_object_entrance(dgi, sender)
        elif msgtype == STATESERVER_OBJECT_CHANGE_ZONE:
            doId = dgi.get_uint32()

            if self.queuePending(doId, dgi, pos):
                self.service.log.debug(f'Queued location change for pending object {doId}.')
                return

            self.handle_location_change(dgi, sender, doId)
        elif msgtype == STATESERVER_QUERY_ZONE_OBJECT_ALL_DONE:
            self.handle_interest_done(dgi)
        elif msgtype == STATESERVER_OBJECT_UPDATE_FIELD:
            doId = dgi.get_uint32()

            if not self.objectExists(doId):
                queued = self.queuePending(doId, dgi, pos)
                if queued:
                    self.service.log.debug(f'Queued field update for pending object {doId}.')
                else:
                    self.service.log.debug(f'Got update for unknown object {doId}.')
                return

            self.handleUpdateField(dgi, sender, doId)
        elif msgtype == STATESERVER_OBJECT_DELETE_RAM:
            doId = dgi.get_uint32()

            if doId == self.avatar_id:
                if sender == self.account.dislId << 32:
                    self.disconnect(ClientDisconnect.RELOGGED, 'redundant login')
                else:
                    self.disconnect(ClientDisconnect.SHARD_DISCONNECT, 'district reset')
            elif not self.objectExists(doId):
                self.service.log.debug(f'Queued deletion for pending object {doId}.')
                self.queue_pending(doId, dgi, pos)
                return
            else:
                self.sendRemoveObject(doId)
                del self.visibleObjects[doId]
        elif msgtype == CLIENT_AGENT_SET_INTEREST:
            self.receive_add_interest(dgi, ai = True)
        elif msgtype == CLIENT_AGENT_REMOVE_INTEREST:
            self.receive_remove_interest(dgi, ai = True)
        elif msgtype in {CLIENT_FRIEND_ONLINE, CLIENT_FRIEND_OFFLINE, CLIENT_GET_FRIEND_LIST_RESP, CLIENT_GET_AVATAR_DETAILS_RESP}:
            dg = Datagram()
            dg.addUint16(msgtype)
            dg.add_bytes(dgi.getRemainingBytes())
            self.send_datagram(dg)
        else:
           self.service.log.debug(f'Client {self.channel} received unhandled upstream msg {msgtype}.')

    def handleUpdateField(self, dgi, sender, doId):
        if sender == self.channel:
            return

        if not self.objectExists(doId):
            self.service.log.debug(f'Got field update for unknown object {doId}')

        pos = dgi.getCurrentIndex()

        fieldNumber = dgi.getUint16()
        field = self.service.dcFile.getFieldByIndex(fieldNumber)

        resp = Datagram()
        resp.addUint16(CLIENT_OBJECT_UPDATE_FIELD)
        resp.addUint32(doId)
        resp.addUint16(fieldNumber)
        resp.appendData(dgi.getRemainingBytes())

        self.send_datagram(resp)

    def handle_owned_object_entrance(self, dgi, sender):
        doId = dgi.get_uint32()
        parentId = dgi.get_uint32()
        zoneId = dgi.get_uint32()
        dcId = dgi.get_uint16()

        self.ownedObjects[doId] = ObjectInfo(doId, dcId, parentId, zoneId)

        resp = Datagram()
        resp.addUint16(CLIENT_GET_AVATAR_DETAILS_RESP)
        resp.addUint32(self.avatar_id)
        resp.add_uint8(0) # Return code
        resp.add_bytes(dgi.remaining_bytes())
        self.send_datagram(resp)

    def handle_location_change(self, dgi, sender, doId):
        new_parent = dgi.get_uint32()
        new_zone = dgi.get_uint32()
        old_parent = dgi.get_uint32()
        old_zone = dgi.get_uint32()
        self.service.log.debug(f'Handle location change for {doId}: ({old_parent} {old_zone}) -> ({new_parent} {new_zone})')

        disable = True

        for interest in self.interests:
            if interest.parentId == new_parent and new_zone in interest.zones:
                disable = False
                break

        visible = doId in self.visibleObjects
        owned = doId in self.ownedObjects

        if not visible and not owned:
            self.service.log.debug(f'Got location change for unknown object {doId}')
            return

        if visible:
            self.visibleObjects[doId].parentId = new_parent
            self.visibleObjects[doId].zoneId = new_zone

        if owned:
            self.ownedObjects[doId].parentId = new_parent
            self.ownedObjects[doId].zoneId = new_zone

        if disable and visible:
            if owned:
                self.send_object_location(doId, new_parent, new_zone)
                return
            self.service.log.debug(f'Got location change and object is no longer visible. Disabling {doId}')
            self.sendRemoveObject(doId)
            del self.visibleObjects[doId]
        else:
            self.send_object_location(doId, new_parent, new_zone)

    def sendRemoveObject(self, doId):
        self.service.log.debug(f'Sending removal of {doId}.')
        resp = Datagram()
        resp.addUint16(CLIENT_OBJECT_DISABLE)
        resp.addUint32(doId)
        self.send_datagram(resp)

    def send_object_location(self, doId, new_parent, new_zone):
        resp = Datagram()
        resp.addUint16(CLIENT_OBJECT_LOCATION)
        resp.addUint32(doId)
        resp.addUint32(new_parent)
        resp.addUint32(new_zone)
        self.send_datagram(resp)

    def handle_interest_done(self, dgi):
        handle = dgi.getUint16()
        context = dgi.getUint32()
        self.service.log.debug(f'sending interest done for handle {handle} context {context}')

        interest = None

        for _interest in self.interests:
            if _interest.handle == handle and _interest.context == context:
                interest = _interest
                break

        if not interest:
            self.service.log.debug(f'Got interest done for unknown interest: {handle} {context}')
            return

        if interest.done:
            self.service.log.debug('Received duplicate interest done...')
            return

        interest.done = True

        pending = [self.pendingObjects.pop(doId) for doId in interest.pendingObjects if doId in self.pendingObjects]
        # Need this sorting.
        pending.sort(key = lambda p: p.dcId)
        del interest.pendingObjects[:]

        self.service.log.debug(f'Replaying datagrams for {[p.doId for p in pending]}')

        for pendingObject in pending:
            for datagram in pendingObject.datagrams:
                self.handle_datagram(datagram, DatagramIterator(datagram))

        if not interest.ai:
            resp = Datagram()
            resp.addUint16(CLIENT_DONE_INTEREST_RESP)
            resp.addUint16(handle)
            resp.addUint32(context)
            self.send_datagram(resp)

    def lookupInterest(self, parentId, zoneId):
        return [interest for interest in self.interests if interest.parentId == parentId and zoneId in interest.zones]

    def handleObjectEntrance(self, dgi, sender):
        # Before msgtype and sender
        pos = dgi.getCurrentIndex() - 10
        hasOther = dgi.getUint8()
        doId = dgi.getUint32()
        parentId = dgi.getUint32()
        zoneId = dgi.getUint32()
        dcId = dgi.getUint16()

        pendingInterests = list(self.getPendingInterests(parentId, zoneId))

        if len(pendingInterests):
            self.service.log.debug(f'Queueing object generate for {doId} in ({parentId} {zoneId}) {doId in self.visibleObjects}')
            pendingObject = PendingObject(doId, dcId, parentId, zoneId, datagrams = [])

            dg = Datagram(dgi.getDatagram().getMessage()[pos:])

            pendingObject.datagrams.append(dg)
            self.pendingObjects[doId] = pendingObject

            for interest in pendingInterests:
                interest.pendingObjects.append(doId)
            return

        if self.objectExists(doId):
            return

        self.visibleObjects[doId] = ObjectInfo(doId, dcId, parentId, zoneId)

        self.sendObjectEntrance(parentId, zoneId, dcId, doId, dgi, hasOther)

    def getPendingInterests(self, parentId, zoneId):
        for interest in self.interests:
            if not interest.done and interest.parentId == parentId and zoneId in interest.zones:
                yield interest

    def objectExists(self, doId):
        return doId in self.visibleObjects or doId in self.ownedObjects or doId in self.uberdogs

    def queuePending(self, doId, dgi, pos):
        if doId in self.pendingObjects:
            _dg = Datagram(dgi.getRemainingBytes())
            dg = DatagramIterator(_dg).getDatagram()
            self.pendingObjects[doId].datagrams.append(dg)
            return True
        return False

    def pending_object_needed(self, doId):
        for interest in self.interests:
            if doId in interest.pendingObjects:
                return True

        return False

    def sendObjectEntrance(self, parentId, zoneId, dcId, doId, dgi, hasOther):
        resp = Datagram()
        resp.addUint16(CLIENT_CREATE_OBJECT_REQUIRED_OTHER if hasOther else CLIENT_CREATE_OBJECT_REQUIRED)
        resp.addUint32(parentId)
        resp.addUint32(zoneId)
        resp.addUint16(dcId)
        resp.addUint32(doId)
        resp.appendData(dgi.getRemainingBytes())
        self.send_datagram(resp)

    def get_potential_avatar(self, avId):
        for potAv in self.potential_avatars:
            if potAv and potAv.doId == avId:
                return potAv

    def send_go_get_lost(self, booted_index, booted_text):
        resp = Datagram()
        resp.addUint16(CLIENT_GO_GET_LOST)
        resp.addUint16(booted_index)
        resp.add_string16(booted_text.encode('utf-8'))
        self.send_datagram(resp)

    def annihilate(self):
        self.service.upstream.unsubscribe_all(self)

    def receiveSetWishNameClear(self, dgi):
        avatarId = dgi.get_uint32()
        actionFlag = dgi.get_uint8()

        # Send this to the Database server.
        resp = Datagram()
        resp.add_server_header([DBSERVERS_CHANNEL], self.channel, DBSERVER_WISHNAME_CLEAR)
        resp.addUint32(avatarId)
        resp.add_uint8(actionFlag)
        self.service.send_datagram(resp)

    def receiveGetObjectDetails(self, dgi, msgType: int):
        doId = dgi.get_uint32()
        access = 2 if self.account.access == b'FULL' else 1
        dclass = messageToClass[msgType]

        # Send this to the Database server.
        resp = Datagram()
        resp.add_server_header([DBSERVERS_CHANNEL], self.channel, DBSERVER_GET_AVATAR_DETAILS)
        resp.addUint32(self.avatar_id)
        resp.addUint32(doId)
        resp.add_uint8(access)
        resp.add_string16(dclass)
        self.service.send_datagram(resp)