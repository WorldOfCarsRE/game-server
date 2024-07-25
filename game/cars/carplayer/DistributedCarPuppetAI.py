from .DistributedCarGMAI import DistributedCarGMAI

class DistributedCarPuppetAI(DistributedCarGMAI):
    def __init__(self, air):
        DistributedCarGMAI.__init__(self, air)
