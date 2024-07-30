from direct.distributed.DistributedObjectUD import DistributedObjectUD
import time

class HolidayManagerUD(DistributedObjectUD):
    def __init__(self, air) -> None:
        DistributedObjectUD.__init__(self, air)

    def getHolidayEvents(self):
        return [['car_show_off_week_1', time.time(), time.time()]]
