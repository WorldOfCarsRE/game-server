from otp import config
from pymongo import MongoClient

client = MongoClient(config['MongoDB.Host'])[config['MongoDB.Name']]

code = {}
code['_id'] = 'sweet'
code['Expired'] = False
code['UsedBy'] = []
code['Items'] = [
    ['CatalogBeanItem', 12000]
]

client.CodeRedemption.insert_one(code)