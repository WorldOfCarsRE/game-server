from direct.distributed.DistributedObjectAI import DistributedObjectAI
import time

class HolidayManagerAI(DistributedObjectAI):
    def __init__(self, air) -> None:
        DistributedObjectAI.__init__(self, air)

    def getHolidayEvents(self):
        return [['car_show_off_week_1', time.time(), time.time()]]
