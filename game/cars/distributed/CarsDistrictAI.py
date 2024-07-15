from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.task import Task
from game.otp.distributed.OtpDoGlobals import *
from game.otp.distributed.DistributedDistrictAI import DistributedDistrictAI

class CarsDistrictAI(DistributedDistrictAI):
    notify = directNotify.newCategory("CarsDistrictAI")

    def __init__(self, air, name="untitled"):
        DistributedDistrictAI.__init__(self, air, name)
        self.enabled = 0

    def generate(self):
        DistributedDistrictAI.generate(self)
        self.air.registerShard()

    def delete(self):
        DistributedDistrictAI.delete(self)

    def setEnabled(self, enabled):
        self.enabled = enabled
        self.air.updateShard()

    def getEnabled(self):
        return self.enabled

    def d_setEnabled(self, enabled):
        self.sendUpdate("setEnabled", [enabled])

    def b_setEnabled(self, enabled):
         self.setEnabled(enabled)
         self.d_setEnabled(enabled)
