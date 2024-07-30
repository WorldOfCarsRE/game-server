"""
The Cars Uber Distributed Object Globals server.
"""

from direct.directnotify.DirectNotifyGlobal import directNotify

from game.otp.distributed.OtpDoGlobals import OTP_DO_ID_CARS_HOLIDAY_MANAGER
from game.otp.uberdog.UberDog import UberDog

from game.cars.distributed.CarsGlobals import *

class CarsUberDog(UberDog):
    notify = directNotify.newCategory("UberDog")

    def __init__(
            self, mdip, mdport, esip, esport, dcFilenames,
            serverId, minChannel, maxChannel):
        assert self.notify.debugStateCall(self)

        UberDog.__init__(
            self, mdip, mdport, esip, esport, dcFilenames,
            serverId, minChannel, maxChannel)

    def createObjects(self):
        UberDog.createObjects(self)

        # Ask for the ObjectServer so we can check the dc hash value
        context = self.allocateContext()
        self.queryObjectAll(self.serverId, context)

        self.holidayManager = self.generateGlobalObject(OTP_DO_ID_CARS_HOLIDAY_MANAGER, "HolidayManager")
