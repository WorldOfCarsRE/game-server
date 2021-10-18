from otp import config
from pymongo import MongoClient

from typing import Tuple, List
import warnings
from .exceptions import *

class DatabaseBackend:
    def __init__(self, service):
        self.service = service
        self.dc = self.service.dc

    async def setup(self):
        raise NotImplementedError

    async def create_object(self, dclass, fields: Tuple[Tuple[str, bytes]]):
        raise NotImplementedError

    def query_object_all(self, do_id: int):
        raise NotImplementedError

    def query_object_fields(self, do_id: int, fields):
        raise NotImplementedError

    def set_field(self, do_id: int, field: str, value: bytes):
        raise NotImplementedError

    def set_fields(self, do_id: int, fields: Tuple[Tuple[str, bytes]]):
        raise NotImplementedError

class MongoBackend(DatabaseBackend):
    def __init__(self, service):
        DatabaseBackend.__init__(self, service)
        self.mongodb = None

    async def setup(self):
        client = MongoClient(config['MongoDB.Host'])
        self.mongodb = client[config['MongoDB.Name']]

    async def _query_dclass(self, do_id: int) -> str:
        cursor = self.mongodb.objects
        fields = cursor.find_one({'do_id': do_id})
        return fields['class_name']

    async def create_object(self, dclass, fields: List[Tuple[str, bytes]]):
        columns = [field[0] for field in fields]

        for field in dclass.inherited_fields:
            if field.is_db and field.is_required:
                if field.name not in columns:
                    raise OTPCreateFailed('Missing required db field: %s' % field.name)

        count = self.mongodb.objects.count()

        data = {}
        data['class_name'] = dclass.name
        data['do_id'] = count + 1
        self.mongodb.objects.insert_one(data)

        dcData = {}
        dcData['do_id'] = count + 1
        dcData['DcObjectType'] = dclass.name

        for field in fields:
            fieldName = field[0]
            dcData[fieldName] = field[1]

        table = getattr(self.mongodb, dclass.name)
        table.insert_one(dcData)

        return count + 1

    async def query_object_all(self, do_id, dclass_name=None):
        if dclass_name is None:
            dclass_name = await self._query_dclass(do_id)

        try:
            cursor = getattr(self.mongodb, dclass_name)
        except:
            raise OTPQueryFailed('Tried to query with invalid dclass name: %s' % dclass_name)

        fields = cursor.find_one({'do_id': do_id})
        return fields

    async def query_object_fields(self, do_id, field_names, dclass_name=None):
        if dclass_name is None:
            dclass_name = await self._query_dclass(do_id)

        cursor = getattr(self.mongodb, dclass_name)
        fields = cursor.find_one({'do_id': do_id})

        values = {}

        for fieldName in field_names:
            if fieldName in fields:
                values[fieldName] = fields[fieldName]

        return values

    async def set_field(self, do_id, field_name, value, dclass_name=None):
        if dclass_name is None:
            dclass_name = await self._query_dclass(do_id)

        queryData = {'do_id': do_id}
        updatedVal = {'$set': {field_name: value}}

        table = getattr(self.mongodb, dclass_name)
        table.update_one(queryData, updatedVal)

    async def set_fields(self, do_id, fields, dclass_name=None):
        if dclass_name is None:
            dclass_name = await self._query_dclass(do_id)

        queryData = {'do_id': do_id}
        table = getattr(self.mongodb, dclass_name)

        for fieldName, value in fields:
            updatedVal = {'$set': {fieldName: value}}
            table.update_one(queryData, updatedVal)