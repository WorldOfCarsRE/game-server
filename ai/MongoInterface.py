from otp import config
from pymongo import MongoClient

class MongoInterface:
    def __init__(self, air):
        self.air = air

        client = MongoClient(config['MongoDB.Host'])
        self.mongodb = client[config['MongoDB.Name']]

    def retrieveFields(self, dclass: str, doId: int) -> list:
        cursor = getattr(self.mongodb, dclass)

        fields = cursor.find_one({'do_id': doId})
        return fields