from ai.DistributedObjectGlobalAI import DistributedObjectGlobalAI
from otp.constants import OTP_DO_ID_CARS_SHARD_MANAGER
from .DistributedObjectAI import DistributedObjectAI
from direct.directnotify.DirectNotifyGlobal import directNotify

class DistributedDistrictAI(DistributedObjectAI):

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.name = ''
        self.available = False

    def d_setName(self, name):
        self.sendUpdate('setName', [name])

    def b_setName(self, name):
        self.name = name
        self.d_setName(name)

    def getName(self):
        return self.name

    def d_setAvailable(self, available):
        self.sendUpdate('setAvailable', [available])

    def b_setAvailable(self, available):
        self.available = available
        self.d_setAvailable(available)

    def getAvailable(self):
        return self.available

    def getEnabled(self):
        return self.available

class CarsDistrictAI(DistributedDistrictAI):
    notify = directNotify.newCategory('CarsDistrictAI')

    def __init__(self, air):
        DistributedDistrictAI.__init__(self, air)

    def handleChildArrive(self, obj, zoneId):
        pass
        # if isinstance(obj, DistributedCarPlayer):
            # obj.sendUpdate('arrivedOnDistrict', [self.doId])
            # self.air.incrementPopulation()

class DistrictManagerAI(DistributedObjectGlobalAI):
    doId = OTP_DO_ID_CARS_SHARD_MANAGER

    def getAllShardsRequest(self, context):
        print(f'getAllShardsRequest - {context}')