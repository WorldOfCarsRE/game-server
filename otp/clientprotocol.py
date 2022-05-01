import json
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Union, Dict, Tuple

from dataslots import with_slots
from panda3d.direct import DCPacker
from panda3d.core import Datagram, DatagramIterator

from otp import config, uberdog
from otp.messagedirector import MDParticipant
from otp.messagetypes import *
from otp.networking import CarsProtocol, DatagramFuture
from otp.zone import *
from otp.constants import *
from otp.util import *

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
    playToken: str
    _id: int
    access: str
    accountType: str
    createFriendsWithChat: str
    chatCodeCreationRule: str
    whitelistChatEnabled: str
    avatarId: int
    racecarId: int
    playerStatusId: int

class ClientProtocol(CarsProtocol, MDParticipant):
    def __init__(self, service):
        CarsProtocol.__init__(self, service)
        MDParticipant.__init__(self, service)

        self.state: int = ClientState.NEW
        self.channel: int = service.newChannelId()
        self.alloc_channel = self.channel
        self.subscribeChannel(self.channel)

        self.interests: List[Interest] = []
        self.visibleObjects: Dict[int, ObjectInfo] = {}
        self.ownedObjects: Dict[int, ObjectInfo] = {}

        # TODO: make this configurable
        self.uberdogs: List[int] = [
            OTP_DO_ID_FRIEND_MANAGER,
            OTP_DO_ID_CARS_SHARD_MANAGER,
            OTP_DO_ID_CARS_HOLIDAY_MANAGER
        ]

        self.account: Union[DISLAccount, None] = None
        self.avatarId: int = 0
        self.racecarId: int = 0
        self.playerStatusId: int = 0
        self.wantedName: str = ''
        self.avsDeleted: List[Tuple[int, int]] = []
        self.pendingObjects: Dict[int, PendingObject] = {}

    def disconnect(self, bootedIndex, bootedText):
        for task in self.tasks:
            task.cancel()
        del self.tasks[:]
        resp = Datagram()
        resp.addUint16(CLIENT_GO_GET_LOST)
        resp.addUint16(bootedIndex)
        resp.addString(bootedText)
        self.transport.write(resp.getLength().to_bytes(2, byteorder = 'little'))
        self.transport.write(resp.getMessage())
        self.transport.close()
        self.service.log.debug(f'Booted client {self.channel} with index {bootedIndex} and text: "{bootedText}"')

    def connection_lost(self, exc):
        self.service.log.debug(f'Connection lost to client {self.channel}')
        CarsProtocol.connection_lost(self, exc)

        if self.avatarId and self.racecarId and self.playerStatusId:
            self.deleteObject(self.avatarId)
            self.deleteObject(self.racecarId)
            self.deleteObject(self.playerStatusId)

        self.service.removeParticipant(self)

    def connection_made(self, transport):
        CarsProtocol.connection_made(self, transport)
        self.subscribeChannel(CLIENTS_CHANNEL)

    def deleteObject(self, doId: int):
        dg = Datagram()
        addServerHeader(dg, [doId], self.channel, STATESERVER_OBJECT_DELETE_RAM)
        dg.addUint32(doId)
        self.service.sendDatagram(dg)

    def receiveDatagram(self, dg):
        dgi = DatagramIterator(dg)
        msgtype = dgi.getUint16()

        print(MSG_TO_NAME_DICT[msgtype])

        if msgtype != CLIENT_OBJECT_UPDATE_FIELD:
            self.service.log.debug(f'Got message type {MSG_TO_NAME_DICT[msgtype]} from client {self.channel}')

        if msgtype == CLIENT_HEARTBEAT:
            self.sendDatagram(dg)
            return

        if msgtype == CLIENT_DISCONNECT:
            return

        if self.state == ClientState.NEW:
            if msgtype == CLIENT_LOGIN_CARS:
                self.receiveLogin(dgi)
                self.state = ClientState.AUTHENTICATED
            else:
                self.service.log.debug(f'Unexpected message type during handshake {msgtype}.')
        elif self.state == ClientState.AUTHENTICATED:
            if msgtype == CLIENT_GET_AVATARS:
                self.receiveGetAvatars(dgi)
            elif msgtype == CLIENT_ADD_INTEREST:
                self.receiveAddInterest(dgi)
            elif msgtype == CLIENT_REMOVE_INTEREST:
                self.receiveRemoveInterest(dgi)
            elif msgtype == CLIENT_OBJECT_UPDATE_FIELD:
                self.receiveUpdateField(dgi)
            else:
                self.service.log.debug(f'Unexpected message type during post authentication {msgtype}.')
        elif self.state == ClientState.AVATAR_CHOOSER:
            if msgtype == CLIENT_CREATE_AVATAR:
                self.receiveCreateAvatar(dgi)
            elif msgtype == CLIENT_SET_WISHNAME:
                self.receiveSetWishName(dgi)
            elif msgtype == CLIENT_REMOVE_INTEREST:
                self.receiveRemoveInterest(dgi)
            elif msgtype == CLIENT_OBJECT_UPDATE_FIELD:
                doId = dgi.getUint32()
                if doId == OTP_DO_ID_CENTRAL_LOGGER:
                    self.receiveUpdateField(dgi, doId)
                else:
                    self.service.log.debug(f'Unexpected field update for doId {doId} during avatar chooser.')
            elif msgtype == CLIENT_DELETE_AVATAR:
                self.receiveDeleteAvatar(dgi)
            elif msgtype == CLIENT_SET_WISHNAME_CLEAR:
                self.receiveSetWishNameClear(dgi)
            else:
                self.service.log.debug(f'Unexpected message type during avatar chooser {msgtype}.')
        elif self.state == ClientState.CREATING_AVATAR:
            if msgtype == CLIENT_SET_WISHNAME:
                self.receiveSetWishName(dgi)
            elif msgtype == CLIENT_OBJECT_UPDATE_FIELD:
                doId = dgi.getUint32()
                if doId == OTP_DO_ID_CENTRAL_LOGGER:
                    self.receiveUpdateField(dgi, doId)
                else:
                    self.service.log.debug(f'Unexpected field update for doId {doId} during avatar creation.')
            else:
                self.service.log.debug(f'Unexpected message type during avatar creation {msgtype}.')
        else:
            if msgtype == CLIENT_ADD_INTEREST:
                self.receiveAddInterest(dgi)
            elif msgtype == CLIENT_REMOVE_INTEREST:
                self.receiveRemoveInterest(dgi)
            elif msgtype == CLIENT_GET_FRIEND_LIST:
                self.receiveGetFriendList(dgi)
            elif msgtype == CLIENT_SET_LOCATION:
                self.receiveClientSetLocation(dgi)
            elif msgtype == CLIENT_OBJECT_UPDATE_FIELD:
                self.receiveUpdateField(dgi)
            elif msgtype in (CLIENT_GET_AVATAR_DETAILS, CLIENT_GET_PET_DETAILS):
                self.receiveGetObjectDetails(dgi, msgtype)
            else:
                self.service.log.debug(f'Unhandled msg type {msgtype} in state {self.state}')

    def receiveUpdateField(self, dgi, doId = None):
        if doId is None:
            doId = dgi.getUint32()

        fieldNumber = dgi.getUint16()

        field = self.service.dcFile.getFieldByIndex(fieldNumber)

        sendable = False

        if field.isOwnsend() and doId in self.ownedObjects:
            sendable = True
        elif field.isClsend():
            sendable = True

        if not sendable:
            self.disconnect(ClientDisconnect.INTERNAL_ERROR, 'Tried to send nonsendable field to object.')
            self.service.log.warn(f'Client {self.channel} tried to update {doId} with nonsendable field {field.getName()}')
            return

        resp = Datagram()
        addServerHeader(resp, [doId], self.channel, STATESERVER_OBJECT_UPDATE_FIELD)
        resp.addUint32(doId)
        resp.addUint16(fieldNumber)
        resp.appendData(dgi.getRemainingBytes())
        self.service.sendDatagram(resp)

        print(field.getName())

        if field.getName() == 'setTalk':
            # TODO: filtering
            resp = Datagram()
            resp.addUint16(CLIENT_OBJECT_UPDATE_FIELD)
            resp.addUint32(doId)
            resp.addUint16(fieldNumber)
            resp.appendData(dgi.getRemainingBytes())
            self.sendDatagram(resp)

    def receiveClientSetLocation(self, dgi):
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
            self.service.sendDatagram(dg)
        else:
            self.service.log.debug(f'Client {self.channel} tried setting location for unowned object {doId}!')

    def setRaceCar(self, racecarId: int):
        self.service.log.debug(f'client {self.channel} is setting their racecar to {racecarId}')

        if not racecarId:
            if self.racecarId:
                # Client is logging out of their racecar.
                self.deleteObject(self.racecarId)
                self.ownedObjects.clear()
                self.visibleObjects.clear()

                self.unsubscribeChannel(getClientSenderChannel(self.account._id, self.avatarId))
                self.unsubscribeChannel(getPuppetChannel(self.avatarId))
                self.channel = getClientSenderChannel(self.account._id, 0)
                self.subscribeChannel(self.channel)

                self.state = ClientState.AUTHENTICATED
                self.avatarId = 0
                return
            else:
                # Do nothing.
                return
        elif self.state == ClientState.PLAY_GAME:
            self.service.log.debug(f'Client {self.channel} tried to set their racecar {racecarId} while racecar is already set to {self.racecarId}.')
            return

        self.racecarId = racecarId

        self.state = ClientState.SETTING_AVATAR

        self.channel = getClientSenderChannel(self.account._id, self.racecarId)
        self.subscribeChannel(self.channel)
        self.subscribeChannel(getPuppetChannel(self.racecarId))

        dclass = self.service.dcFile.getClassByName('DistributedRaceCar')

        # These Fields are REQUIRED but not stored in db.
        otherFields = []

        self.activateDatabaseObjectWithOther(racecarId, dclass, otherFields)

    def setAvatar(self, avId: int):
        self.service.log.debug(f'client {self.channel} is setting their avatar to {avId}')

        if not avId:
            if self.avatarId:
                # Client is logging out of their avatar.
                self.deleteObject(self.avatarId)
                self.ownedObjects.clear()
                self.visibleObjects.clear()

                self.unsubscribeChannel(getClientSenderChannel(self.account._id, self.avatarId))
                self.unsubscribeChannel(getPuppetChannel(self.avatarId))
                self.channel = getClientSenderChannel(self.account._id, 0)
                self.subscribeChannel(self.channel)

                self.state = ClientState.AUTHENTICATED
                self.avatarId = 0
                return
            else:
                # Do nothing.
                return
        elif self.state == ClientState.PLAY_GAME:
            self.service.log.debug(f'Client {self.channel} tried to set their avatar {avId} while avatar is already set to {self.avatarId}.')
            return

        self.avatarId = avId

        self.state = ClientState.SETTING_AVATAR

        self.channel = getClientSenderChannel(self.account._id, self.avatarId)
        self.subscribeChannel(self.channel)
        self.subscribeChannel(getPuppetChannel(self.avatarId))

        dclass = self.service.dcFile.getClassByName('DistributedCarPlayer')

        access = 2 if self.account.access == 'FULL' else 1

        # These Fields are REQUIRED but not stored in db.
        otherFields = [
            (dclass.getFieldByName('setTelemetry'), (0, 0, 0, 0, 0, 0, 0, 0,)),
            (dclass.getFieldByName('setPhysics'), ([], [], [], [], [],)),
            (dclass.getFieldByName('setState'), (0,))
        ]

        self.activateDatabaseObjectWithOther(avId, dclass, otherFields)

    def packFieldData(self, field, data):
        packer = DCPacker()
        packer.rawPackUint16(field.getNumber())

        packer.beginPack(field)

        field.packArgs(packer, data)

        packer.endPack()

        return packer.getBytes()

    def receiveRemoveInterest(self, dgi, ai = False):
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

        uninterestedZones = []

        for zone in interest.zones:
            if len(self.lookupInterest(parentId, zone)) == 1:
                uninterestedZones.append(zone)

        toRemove = []

        for doId in self.visibleObjects:
            do = self.visibleObjects[doId]
            if do.parentId == parentId and do.zoneId in uninterestedZones:
                self.service.log.debug(f'Object {doId} killed by interest remove.')
                self.sendRemoveObject(doId)

                toRemove.append(doId)

        for doId in toRemove:
            del self.visibleObjects[doId]

        for zone in uninterestedZones:
            self.unsubscribeChannel(locationAsChannel(parentId, zone))

        self.interests.remove(interest)

        if not ai:
            resp = Datagram()
            resp.addUint16(CLIENT_DONE_INTEREST_RESP)
            resp.addUint16(handle)
            resp.addUint32(context)
            self.sendDatagram(resp)

    def receiveLogin(self, dgi):
        playToken = dgi.getString()
        clientVersion = dgi.getString()
        hashVal = dgi.getUint32()
        tokenType = dgi.getUint32()
        _ = dgi.getString()

        self.service.log.debug(f'playToken:{playToken}, clientVersion:{clientVersion}, hashVal:{hashVal}')

        if clientVersion != str(self.service.version):
            self.disconnect(ClientDisconnect.OUTDATED_CLIENT, 'Version mismatch')
            return

        if tokenType != CLIENT_LOGIN_3_DISL_TOKEN:
            self.disconnect(ClientDisconnect.LOGIN_ERROR, 'Invalid token')
            return

        if hashVal != self.service.dcHash:
            self.disconnect(ClientDisconnect.LOGIN_ERROR, '')
            return

        # Send this to the Database server.
        resp = Datagram()
        addServerHeader(resp, [DBSERVERS_CHANNEL], self.channel, DBSERVER_AUTH_REQUEST)
        resp.addString(playToken)
        self.service.sendDatagram(resp)

    def handleLoginResp(self, dgi):
        data = json.loads(dgi.getString())

        self.service.log.debug(f'Login token data:{data}')

        for key in list(data.keys()):
            value = data[key]

            if type(value) == str:
                data[key] = value

        self.account = DISLAccount(**data)

        resp = Datagram()
        resp.addUint16(CLIENT_LOGIN_CARS_RESP)

        returnCode = 0  # -13 == period expired
        resp.addUint8(returnCode)

        errorString = '' # 'Bad DC Version Compare'
        resp.addString(errorString)

        resp.addUint32(self.account.avatarId) # Avatar Id
        resp.addUint32(self.account._id)

        resp.addString(self.account.playToken)

        accountNameApproved = True
        resp.addUint8(accountNameApproved)

        resp.addString(self.account.whitelistChatEnabled)
        resp.addString(self.account.createFriendsWithChat)
        resp.addString(self.account.chatCodeCreationRule)

        resp.addString(self.account.access)
        resp.addString(self.account.whitelistChatEnabled)

        self.channel = getClientSenderChannel(self.account._id, 0)
        self.subscribeChannel(self.channel)
        self.subscribeChannel(getAccountChannel(self.account._id))

        self.sendDatagram(resp)

        self.setAvatar(self.account.avatarId)
        self.setRaceCar(self.account.racecarId)

        dclass = self.service.dcFile.getClassByName('CarPlayerStatus')

        self.playerStatusId = self.account.playerStatusId

        self.activateDatabaseObjectWithOther(self.account.playerStatusId, dclass, [])

    def activateDatabaseObjectWithOther(self, doId: int, dclass, other: list):
        dg = Datagram()
        addServerHeader(dg, [STATESERVERS_CHANNEL], self.channel, STATESERVER_OBJECT_CREATE_WITH_REQUIR_OTHER_CONTEXT)
        dg.addUint32(doId)
        dg.addUint32(0)
        dg.addUint32(0)
        dg.addUint64(self.channel)
        dg.addUint16(dclass.getNumber())
        dg.addUint16(len(other))

        for f, arg in other:
            packer = DCPacker()
            packer.rawPackUint16(f.getNumber())

            packer.beginPack(f)
            f.packArgs(packer, arg)
            packer.endPack()

            dg.appendData(packer.getBytes())

        self.service.sendDatagram(dg)

    def receiveAddInterest(self, dgi, ai = False):
        handle = dgi.getUint16()
        contextId = dgi.getUint32()
        parentId = dgi.getUint32()
        zones = [dgi.getUint32()]

        self.service.log.debug(f'Client {self.channel} is requesting interest with handle {handle} and context {contextId} '
                               f'for location {parentId} {zones}')

        if self.state <= ClientState.AUTHENTICATED and parentId != OTP_DO_ID_FAIRIES:
            self.service.log.debug(f'Client {self.channel} requested unexpected interest in state {self.state}. Ignoring.')
            return

        previousInterest = None

        for _interest in self.interests:
            if _interest.handle == handle:
                previousInterest = _interest
                break

        if previousInterest is None:
            interest = Interest(self.channel, handle, contextId, parentId, zones)
            self.interests.append(interest)
        else:
            self.service.log.debug(f'Altering interest {handle} (done: {previousInterest.done}): {previousInterest.zones} -> {zones}')
            self.interests.remove(previousInterest)

            if previousInterest.parentId != parentId:
                killedZones = previousInterest.zones
            else:
                killedZones = set(previousInterest.zones).difference(set(zones))

            for _interest in self.interests:
                killedZones = killedZones.difference(set(_interest.zones))
                if not killedZones:
                    break

            self.service.log.debug(f'Zones killed by altering interest: {killedZones}')

            if killedZones:
                for doId in list(self.visibleObjects.keys()):
                    obj = self.visibleObjects[doId]
                    if obj.parentId == parentId and obj.zoneId in killedZones:
                        self.service.log.debug(f'Object {obj.doId}, location ({obj.parentId}, {obj.zoneId}), killed by altered interest: {zones}')
                        self.sendRemoveObject(obj.doId)
                        del self.visibleObjects[doId]

            for zone in killedZones:
                self.unsubscribeChannel(locationAsChannel(previousInterest.parentId, zone))

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
                resp.addUint32(contextId)
                self.sendDatagram(resp)
                return

        queryReq = Datagram()
        addServerHeader(queryReq, [parentId], self.channel, STATESERVER_QUERY_ZONE_OBJECT_ALL)
        queryReq.addUint16(handle)
        queryReq.addUint32(contextId)
        queryReq.addUint32(parentId)

        for zone in zones:
            queryReq.addUint32(zone)
            self.subscribeChannel(locationAsChannel(parentId, zone))

        self.service.sendDatagram(queryReq)

    def handleDatagram(self, dg, dgi):
        pos = dgi.getCurrentIndex()
        sender = dgi.getInt64()

        if sender == self.channel:
            return

        msgtype = dgi.getUint16()

        self.checkFutures(dgi, msgtype, sender)

        if msgtype == STATESERVER_OBJECT_ENTERZONE_WITH_REQUIRED_OTHER:
            self.handleObjectEntrance(dgi, sender)
        elif msgtype == STATESERVER_OBJECT_ENTER_OWNER_RECV:
            self.handleOwnedObjectEntry(dgi, sender)
        elif msgtype == STATESERVER_OBJECT_CHANGE_ZONE:
            doId = dgi.getUint32()

            if self.queuePending(doId, dgi, pos):
                self.service.log.debug(f'Queued location change for pending object {doId}.')
                return

            self.handleLocationChange(dgi, sender, doId)
        elif msgtype == STATESERVER_QUERY_ZONE_OBJECT_ALL_DONE:
            self.handleInterestDone(dgi)
        elif msgtype == STATESERVER_OBJECT_UPDATE_FIELD:
            doId = dgi.getUint32()

            if not self.objectExists(doId):
                queued = self.queuePending(doId, dgi, pos)
                if queued:
                    self.service.log.debug(f'Queued field update for pending object {doId}.')
                else:
                    self.service.log.debug(f'Got update for unknown object {doId}.')
                return

            self.handleUpdateField(dgi, sender, doId)
        elif msgtype == STATESERVER_OBJECT_DELETE_RAM:
            doId = dgi.getUint32()

            if doId == self.avatarId or doId == self.racecarId:
                if sender == self.account._id << 32:
                    self.disconnect(ClientDisconnect.RELOGGED, 'redundant login')
                else:
                    self.disconnect(ClientDisconnect.SHARD_DISCONNECT, 'district reset')
            elif not self.objectExists(doId):
                self.service.log.debug(f'Queued deletion for pending object {doId}.')
                self.queuePending(doId, dgi, pos)
                return
            else:
                self.sendRemoveObject(doId)
                del self.visibleObjects[doId]
        elif msgtype == CLIENT_AGENT_SET_INTEREST:
            self.receiveAddInterest(dgi, ai = True)
        elif msgtype == CLIENT_AGENT_REMOVE_INTEREST:
            self.receiveRemoveInterest(dgi, ai = True)
        elif msgtype == CLIENT_AGENT_EJECT:
            bootCode, message = dgi.getUint16(), dgi.getString()
            self.disconnect(bootCode, message)
        elif msgtype in {CLIENT_FRIEND_ONLINE, CLIENT_FRIEND_OFFLINE, CLIENT_GET_FRIEND_LIST_RESP, CLIENT_GET_AVATAR_DETAILS_RESP}:
            dg = Datagram()
            dg.addUint16(msgtype)
            dg.appendData(dgi.getRemainingBytes())
            self.sendDatagram(dg)
        elif msgtype == DBSERVER_AUTH_REQUEST_RESP:
            self.handleLoginResp(dgi)
        else:
           self.service.log.debug(f'Client {self.channel} received unhandled upstream msg {msgtype}.')

    def handleUpdateField(self, dgi, sender, doId):
        if sender == self.channel:
            return

        if not self.objectExists(doId):
            self.service.log.debug(f'Got field update for unknown object {doId}')

        fieldNumber = dgi.getUint16()
        field = self.service.dcFile.getFieldByIndex(fieldNumber)

        print('handleUpdateField', field.getName())

        resp = Datagram()
        resp.addUint16(CLIENT_OBJECT_UPDATE_FIELD)
        resp.addUint32(doId)
        resp.addUint16(fieldNumber)
        resp.appendData(dgi.getRemainingBytes())

        self.sendDatagram(resp)

    def handleOwnedObjectEntry(self, dgi, sender):
        doId = dgi.getUint32()
        parentId = dgi.getUint32()
        zoneId = dgi.getUint32()
        dcId = dgi.getUint16()

        self.ownedObjects[doId] = ObjectInfo(doId, dcId, parentId, zoneId)

        dcName = self.service.dcFile.getClass(dcId).getName()

        print(f'Sending owned entry for: {dcName}')

        resp = Datagram()
        resp.addUint16(CLIENT_CREATE_OBJECT_REQUIRED_OTHER_OWNER)
        resp.addUint16(dcId)
        resp.addUint32(doId)
        resp.addUint32(parentId)
        resp.addUint32(zoneId)
        resp.appendData(dgi.getRemainingBytes())
        self.sendDatagram(resp)

    def handleLocationChange(self, dgi, sender, doId):
        newParent = dgi.getUint32()
        newZone = dgi.getUint32()
        oldParent = dgi.getUint32()
        oldZone = dgi.getUint32()
        self.service.log.debug(f'Handle location change for {doId}: ({oldParent} {oldZone}) -> ({newParent} {newZone})')

        disable = True

        for interest in self.interests:
            if interest.parentId == newParent and newZone in interest.zones:
                disable = False
                break

        visible = doId in self.visibleObjects
        owned = doId in self.ownedObjects

        if not visible and not owned:
            self.service.log.debug(f'Got location change for unknown object {doId}')
            return

        if visible:
            self.visibleObjects[doId].parentId = newParent
            self.visibleObjects[doId].zoneId = newZone

        if owned:
            self.ownedObjects[doId].parentId = newParent
            self.ownedObjects[doId].zoneId = newZone

        if disable and visible:
            if owned:
                self.sendObjectLocation(doId, newParent, newZone)
                return
            self.service.log.debug(f'Got location change and object is no longer visible. Disabling {doId}')
            self.sendRemoveObject(doId)
            del self.visibleObjects[doId]
        else:
            self.sendObjectLocation(doId, newParent, newZone)

    def sendRemoveObject(self, doId):
        self.service.log.debug(f'Sending removal of {doId}.')
        resp = Datagram()
        resp.addUint16(CLIENT_OBJECT_DISABLE)
        resp.addUint32(doId)
        self.sendDatagram(resp)

    def sendObjectLocation(self, doId, newParent, newZone):
        resp = Datagram()
        resp.addUint16(CLIENT_SET_LOCATION)
        resp.addUint32(doId)
        resp.addUint32(newParent)
        resp.addUint32(newZone)
        self.sendDatagram(resp)

    def handleInterestDone(self, dgi):
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
                self.handleDatagram(datagram, DatagramIterator(datagram))

        if not interest.ai:
            resp = Datagram()
            resp.addUint16(CLIENT_DONE_INTEREST_RESP)
            resp.addUint16(handle)
            resp.addUint32(context)
            self.sendDatagram(resp)

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

    def pendingObjectNeeded(self, doId):
        for interest in self.interests:
            if doId in interest.pendingObjects:
                return True

        return False

    def sendObjectEntrance(self, parentId, zoneId, dcId, doId, dgi, hasOther):
        dcName = self.service.dcFile.getClass(dcId).getName()
        print(f'Sending entry for: {dcName}')

        resp = Datagram()
        resp.addUint16(CLIENT_CREATE_OBJECT_REQUIRED_OTHER if hasOther else CLIENT_CREATE_OBJECT_REQUIRED)
        resp.addUint32(parentId)
        resp.addUint32(zoneId)
        resp.addUint16(dcId)
        resp.addUint32(doId)
        resp.appendData(dgi.getRemainingBytes())
        self.sendDatagram(resp)

    def sendGoGetLost(self, bootedIndex, bootedText):
        resp = Datagram()
        resp.addUint16(CLIENT_GO_GET_LOST)
        resp.addUint16(bootedIndex)
        resp.addString(bootedText)
        self.sendDatagram(resp)

    def annihilate(self):
        self.service.upstream.unsubscribeAll(self)