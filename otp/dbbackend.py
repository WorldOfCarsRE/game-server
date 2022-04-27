from otp import config
from pymongo import MongoClient

import aiomysql
from typing import Tuple, List
import warnings
from .exceptions import *

class DatabaseBackend:
    def __init__(self, service):
        self.service = service
        self.dc = self.service.dc

    async def setup(self):
        raise NotImplementedError

    async def createObject(self, dclass, fields: Tuple[Tuple[str, bytes]]):
        raise NotImplementedError

    def queryObjectAll(self, doId: int):
        raise NotImplementedError

    def queryObjectFields(self, doId: int, fields):
        raise NotImplementedError

    def setField(self, doId: int, field: str, value: bytes):
        raise NotImplementedError

    def setFields(self, doId: int, fields: Tuple[Tuple[str, bytes]]):
        raise NotImplementedError

class SQLBackend(DatabaseBackend):
    def __init__(self, service):
        DatabaseBackend.__init__(self, service)
        self.pool = None

    async def setup(self):
        self.pool = await aiomysql.create_pool(host=config['SQL.HOST'], port=config['SQL.PORT'], user=config['SQL.USER'],
                                               password=config['SQL.PASSWORD'], loop=self.service.loop, db='otp', maxsize=5)
        conn = await self.pool.acquire()
        cursor = await conn.cursor()

        warnings.filterwarnings('ignore', 'Table \'[A-Za-z]+\' already exists')

        await cursor.execute('SHOW TABLES LIKE \'objects\';')
        if await cursor.fetchone() is None:
            await cursor.execute('CREATE TABLE objects (doId INT NOT NULL AUTO_INCREMENT, class_name VARCHAR(255), PRIMARY KEY (doId));')
            await cursor.execute("ALTER TABLE objects AUTO_INCREMENT = %d;" % self.service.minChannel)

        for dclass in self.dc.classes:
            if 'DcObjectType' not in dclass.fields_by_name:
                continue

            columns = []
            for field in dclass.inherited_fields:
                if field.is_db:
                    columns.append(f'{field.getName()} blob,')

            if not columns:
                continue

            columns = ''.join(columns)
            cmd = f'CREATE TABLE IF NOT EXISTS {dclass.getName()} (doId INT, {columns} PRIMARY KEY (doId), FOREIGN KEY (doId) REFERENCES objects(doId));'
            await cursor.execute(cmd)

        await cursor.close()
        conn.close()
        self.pool.release(conn)

    async def queryDC(self, conn: aiomysql.Connection, doId: int) -> str:
        cursor = await conn.cursor()
        await cursor.execute(f'SELECT class_name FROM objects WHERE doId={doId}')
        await conn.commit()
        dclassName = await cursor.fetchone()
        await cursor.close()

        if dclassName is None:
            conn.close()
            self.pool.release(conn)
            raise OTPQueryNotFound('object %d not found' % doId)

        return dclassName[0]

    async def createObject(self, dclass, fields: List[Tuple[str, bytes]]):
        # TODO: get field default from DC and pack
        columns = [field[0] for field in fields]
        values = ["X'%s'" % field[1].hex().upper() for field in fields]

        for fieldIndex in range(dclass.getNumInheritedFields()):
            field = dclass.getInheritedField(fieldIndex)

            if field.isDb() and field.isRequired():
                if field.getName() not in columns:
                    raise OTPCreateFailed('Missing required db field: %s' % field.getName())

        columns = ', '.join(columns)
        values = ', '.join(values)

        conn = await self.pool.acquire()
        cursor = await conn.cursor()

        cmd = f"INSERT INTO objects (class_name) VALUES ('{dclass.getName()}');"
        try:
            await cursor.execute(cmd)
            await conn.commit()
        except aiomysql.IntegrityError as e:
            await cursor.close()
            conn.close()
            self.pool.release(conn)
            raise OTPCreateFailed('Created failed with error code: %s' % e.args[0])

        await cursor.execute('SELECT LAST_INSERT_ID();')
        doId = (await cursor.fetchone())[0]

        cmd = f'INSERT INTO {dclass.getName()} (doId, DcObjectType, {columns}) VALUES ({doId}, \'{dclass.getName()}\', {values});'

        try:
            await cursor.execute(cmd)
            await conn.commit()
        except aiomysql.IntegrityError as e:
            await cursor.close()
            conn.close()
            self.pool.release(conn)
            raise OTPCreateFailed('Created failed with error code: %s' % e.args[0])

        await cursor.close()
        conn.close()
        self.pool.release(conn)
        return doId

    async def queryObjectAll(self, doId, dclassName = None):
        conn = await self.pool.acquire()

        if dclassName is None:
            dclassName = await self._queryDClass(conn, doId)

        cursor = await conn.cursor(aiomysql.DictCursor)
        try:
            await cursor.execute(f'SELECT * FROM {dclassName} WHERE doId={doId}')
        except aiomysql.ProgrammingError:
            await cursor.close()
            conn.close()
            raise OTPQueryFailed('Tried to query with invalid dclass name: %s' % dclassName)

        fields = await cursor.fetchone()
        await cursor.close()

        conn.close()
        self.pool.release(conn)

        return fields

    async def queryObjectFields(self, doId, fieldNames, dclassName = None):
        conn = await self.pool.acquire()

        if dclassName is None:
            dclassName = await self._queryDClass(conn, doId)

        fieldNames = ", ".join(fieldNames)

        cursor = await conn.cursor(aiomysql.DictCursor)
        await cursor.execute(f'SELECT {fieldNames} FROM {dclassName} WHERE doId={doId}')
        values = await cursor.fetchone()
        await cursor.close()
        conn.close()
        self.pool.release(conn)

        return values

    async def setField(self, doId, fieldName, value, dclassName = None):
        conn = await self.pool.acquire()

        if dclassName is None:
            dclassName = await self._queryDClass(conn, doId)

        cursor = await conn.cursor()

        value = f"X'{value.hex().upper()}'"

        try:
            await cursor.execute(f'UPDATE {dclassName} SET {fieldName} = {value} WHERE doId={doId}')
            await conn.commit()
        except aiomysql.IntegrityError as e:
            await cursor.close()
            conn.close()
            self.pool.release(conn)
            raise OTPQueryFailed('Query failed with error code: %s' % e.args[0])

        await cursor.close()
        conn.close()
        self.pool.release(conn)

    async def setFields(self, doId, fields, dclassName = None):
        conn = await self.pool.acquire()

        if dclassName is None:
            dclassName = await self._queryDClass(conn, doId)

        cursor = await conn.cursor()

        items = ', '.join((f"{fieldName} = X'{value.hex().upper()}'" for fieldName, value in fields))

        try:
            await cursor.execute(f'UPDATE {dclassName} SET {items} WHERE doId={doId}')
            await conn.commit()
        except aiomysql.IntegrityError as e:
            await cursor.close()
            conn.close()
            self.pool.release(conn)
            raise OTPQueryFailed('Query failed with error code: %s' % e.args[0])

        await cursor.close()
        conn.close()
        self.pool.release(conn)

class MongoBackend(DatabaseBackend):
    def __init__(self, service):
        DatabaseBackend.__init__(self, service)
        self.mongodb = None

    async def setup(self):
        client = MongoClient(config['MongoDB.Host'])
        self.mongodb = client[config['MongoDB.Name']]

        # Check if we need to create our initial entries in the database.
        entry = self.mongodb.objects.find_one({'type': 'objectId'})

        if entry is None:
            # We need to create our initial entry.
            self.mongodb.objects.insert_one({'type': 'objectId', 'nextId': self.service.minChannel})

    async def generateObjectId(self):
        returnDoc = self.mongodb.objects.find_one_and_update({'type': 'objectId'}, {'$inc': {'nextId': 1}})
        return returnDoc['nextId']

    async def queryDC(self, doId: int) -> str:
        cursor = self.mongodb.objects
        fields = cursor.find_one({'_id': doId})
        return fields['className']

    async def createObject(self, dclass, fields: List[Tuple[str, bytes]]):
        columns = [field[0] for field in fields]

        for fieldIndex in range(dclass.getNumInheritedFields()):
            field = dclass.getInheritedField(fieldIndex)

            if field.isDb() and field.isRequired():
                if field.getName() not in columns:
                    raise OTPCreateFailed(f'Missing required db field: {field.getName()}')

        objectId = await self.generateObjectId()

        data = {}
        data['_id'] = objectId
        data['className'] = dclass.getName()
        self.mongodb.objects.insert_one(data)

        dcData = {}
        dcData['_id'] = objectId
        dcData['DcObjectType'] = dclass.getName()

        for field in fields:
            fieldName = field[0]
            dcData[fieldName] = field[1]

        table = getattr(self.mongodb, dclass.getName())
        table.insert_one(dcData)

        return objectId

    async def queryObjectAll(self, doId, dclassName = None):
        if dclassName is None:
            dclassName = await self.queryDC(doId)

        try:
            cursor = getattr(self.mongodb, dclassName)
        except:
            raise OTPQueryFailed(f'Tried to query with invalid dclass name: {dclassName}')

        fields = cursor.find_one({'_id': doId})
        return fields

    async def queryObjectFields(self, doId, fieldNames, dclassName = None):
        if dclassName is None:
            dclassName = await self.queryDC(doId)

        cursor = getattr(self.mongodb, dclassName)
        fields = cursor.find_one({'_id': doId})

        values = {}

        for fieldName in fieldNames:
            if fieldName in fields:
                values[fieldName] = fields[fieldName]

        return values

    async def setField(self, doId, fieldName, value, dclassName = None):
        if dclassName is None:
            dclassName = await self.queryDC(doId)

        queryData = {'_id': doId}
        updatedVal = {'$set': {fieldName: value}}

        table = getattr(self.mongodb, dclassName)
        table.update_one(queryData, updatedVal)

    async def setFields(self, doId, fields, dclassName = None):
        if dclassName is None:
            dclassName = await self.queryDC(doId)

        queryData = {'_id': doId}
        table = getattr(self.mongodb, dclassName)

        for fieldName, value in fields:
            updatedVal = {'$set': {fieldName: value}}
            table.update_one(queryData, updatedVal)