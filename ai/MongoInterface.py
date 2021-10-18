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

    def updateField(self, dclass: str, fieldName: str, doId: int, value: list):
        queryData = {'do_id': doId}
        updatedVal = {'$set': {fieldName: value}}

        table = getattr(self.mongodb, dclass)
        table.update_one(queryData, updatedVal)

    def updateFields(self, dclass: str, fields: dict, doId: int):
        queryData = {'do_id': doId}
        cursor = getattr(self.mongodb, dclass)

        for fieldName, value in fields:
            updatedVal = {'$set': {fieldName: value}}
            table.update_one(queryData, updatedVal)