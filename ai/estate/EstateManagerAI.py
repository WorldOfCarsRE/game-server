from ai.DistributedObjectAI import DistributedObjectAI
from otp.constants import DBSERVERS_CHANNEL
from otp.messagetypes import DBSERVER_GET_ESTATE, DBSERVER_UNLOAD_ESTATE
from ai.estate.DistributedEstateAI import DistributedEstateAI
from direct.showbase.PythonUtil import Functor
from panda3d.core import Datagram
from otp.util import addServerHeader

class EstateManagerAI(DistributedObjectAI):

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        # Dict of estate zoneId's keyed by avId.
        self.estateZones: Dict[int] = {}

        # These are used during estate retrieval.
        self.queryContext = 0
        self.queries = {}

        # Dict of DistributedEstateAI's keyed on avId.
        self.estate: Dict[int] = {}

        # Dict of DistributedEstateAI doId's keyed on avId.
        self.avIdToEstate: Dict[int] = {}

    def getEstateZone(self, avId: int, name: str):
        av = self.air.doTable.get(avId)
        accId = self.air.currentAccountSender

        self.acceptOnce(self.air.getDeleteDoIdEvent(avId), self.handleUnexpectedEdit, extraArgs = [avId])

        # Allocate our estate zone.
        self.estateZones[avId] = self.air.allocateZone()

        # Create the estate and generate the zone.
        callback = Functor(self.handleGetEstate, avId)
        self.getEstate(avId, self.estateZones[avId], callback)

    def getEstate(self, avId: int, zone: int, callback: Functor):
        context = self.queryContext
        self.queryContext += 1
        self.queries[context] = callback
        self.sendGetEstate(avId, context, zone)

    def sendGetEstate(self, avId: int, context: int, zone: int):
        dg = Datagram()
        addServerHeader(dg, [DBSERVERS_CHANNEL], self.air.ourChannel, DBSERVER_GET_ESTATE)
        dg.add_uint32(context)
        dg.add_uint32(avId)
        dg.add_uint32(self.parentId)
        dg.add_uint32(zone)
        self.air.send(dg)

    def handleUnexpectedEdit(self, avId: int):
        self.ignore(self.air.getDeleteDoIdEvent(avId))

        self.handleCleanup(avId)

    def exitEstate(self):
        # TODO: This needs to remove visitors.
        avId = self.air.currentAvatarSender

        self.handleCleanup(avId)

    def handleCleanup(self, avId: int):
        if avId in self.estateZones:
            # Deallocate this zone.
            self.air.deallocateZone(self.estateZones[avId])

            # Remove this avatar from our dictionaries.
            del self.estateZones[avId]
            del self.avIdToEstate[avId]

        # Unload our estate.
        dg = Datagram()
        addServerHeader(dg, [DBSERVERS_CHANNEL], self.air.ourChannel, DBSERVER_UNLOAD_ESTATE)
        dg.add_uint32(avId)
        dg.add_uint32(self.parentId)
        self.air.send(dg)

    def handleGetEstateResp(self, dgi):
        context = dgi.getUint32()

        callback = self.queries.get(context)

        if callback:
            del self.queries[context]

            avId = dgi.getUint32()
            estateId = dgi.getUint32()

            self.avIdToEstate[avId] = estateId

            callback()

    def handleGetEstate(self, avId: int):
        self.estate[avId] = self.air.doTable.get(self.avIdToEstate[avId])

        self.sendUpdateToAvatar(avId, 'setEstateZone', [avId, self.estateZones[avId]])

    def removeFriend(self, ownerId, friendId):
        sender = self.air.currentAvatarSender

        if sender != ownerId:
            return

        if friendId == ownerId:
            return

        friend = self.air.doTable.get(friendId)

        if friend:
            self.sendUpdateToAvatar(friendId, 'sendAvToPlayground', [friendId, 1])