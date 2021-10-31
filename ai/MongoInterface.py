from otp import config
from pymongo import MongoClient

class MongoInterface:
    def __init__(self, air):
        self.air = air

        client = MongoClient(config['MongoDB.Host'])
        self.mongodb = client[config['MongoDB.Name']]

    def retrieveFields(self, dclass: str, doId: int) -> list:
        cursor = getattr(self.mongodb, dclass)

        fields = cursor.find_one({'_id': doId})
        return fields

    def findCodeMatch(self, code: str) -> list:
        cursor = getattr(self.mongodb, 'CodeRedemption')

        codeData = cursor.find_one({'_id': code})
        return codeData

    def updateCode(self, code: str, items: list):
        queryData = {'_id': code}
        updatedVal = {'$set': items}

        table = getattr(self.mongodb, 'CodeRedemption')
        table.update_one(queryData, updatedVal)

    def updateField(self, dclass: str, fieldName: str, doId: int, value: list):
        queryData = {'_id': doId}
        updatedVal = {'$set': {fieldName: value}}

        table = getattr(self.mongodb, dclass)
        table.update_one(queryData, updatedVal)

    def updateFields(self, dclass: str, fields: dict, doId: int):
        queryData = {'_id': doId}
        cursor = getattr(self.mongodb, dclass)

        for fieldName, value in fields:
            updatedVal = {'$set': {fieldName: value}}
            table.update_one(queryData, updatedVal)