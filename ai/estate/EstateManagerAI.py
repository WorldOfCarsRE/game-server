from ai.DistributedObjectAI import DistributedObjectAI
from otp.constants import DBSERVERS_CHANNEL
from otp.messagetypes import DBSERVER_GET_ESTATE
from ai.estate.DistributedEstateAI import DistributedEstateAI
from direct.showbase.PythonUtil import Functor
from dc.util import Datagram

class EstateManagerAI(DistributedObjectAI):

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        # Dict of estate zoneId's keyed by avId.
        self.estateZones: Dict[int] = {}

        # These are used during estate retrieval.
        self.queryContext = 0
        self.queries = {}

    def getEstateZone(self, avId: int, name: str):
        av = self.air.doTable.get(avId)
        accId = self.air.currentAccountSender

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
        dg.add_server_header([DBSERVERS_CHANNEL], self.air.ourChannel, DBSERVER_GET_ESTATE)
        dg.add_uint32(context)
        dg.add_uint32(avId)
        dg.add_uint32(self.parentId)
        dg.add_uint32(zone)
        self.air.send(dg)

    def exitEstate(self):
        avId = self.air.currentAvatarSender

        # Deallocate this zone.
        self.air.deallocateZone(self.estateZones[avId])

        # Remove this avatar from our dictionary.
        del self.estateZones[avId]

    def handleGetEstateResp(self, dgi):
        context = dgi.get_uint32()
        callback = self.queries.get(context)

        if callback:
            callback()

    def handleGetEstate(self, avId: int):
        self.sendUpdateToAvatar(avId, 'setEstateZone', [avId, self.estateZones[avId]])