#！usr/env/bin python3
#-*- coding:utf-8 -*-

import logging; logging.basicConfig(level=logging.INFO)
import asyncio, os, json, time, aiomysql, MySQLdb
from datetime import datetime
from aiohttp import web

def log(msg, *args):
    #logging.basicConfig()
    logging.log(logging.INFO, msg, args)

def index(request):
    return web.Response(body=b'<h1>awesome<h1>', content_type='html')

def create_database(L=None,**kw):    
    try:        
        #连接数据库
        db = MySQLdb.connect(
            host='localhost',
            user=kw['user'],
            password=kw['password'],
            charset='utf8'
        )
        db_name = kw['db']
        print(db_name)
        #创建游标
        cursor = db.cursor()
        #执行sql语句
        cursor.execute('show databases')
        rows = cursor.fetchall()
        for row in rows:
            tmp = '%2s'%row
            print('db ==>', row)
            #判断数据库是否存在
            if db_name == tmp:
                db.close()
                return True
        cursor.execute('create database if not exists %s' % db_name)
        print('execute....')
        #提交到数据库执行
        db.commit()
        db.close()
    except Exception as e:
        print(e)
        return False
    return True

def create_database_table():
    pass

@asyncio.coroutine
def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', index)
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server start at http://127.0.0.1:9000 ...')
    return srv

@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool
    __pool = yield from aiomysql.create_pool(
        host = kw.get('host', 'localhost'),
        port = kw.get('port', 3306),
        user = kw['user'],
        password = kw['password'],
        db = kw['db'],
        charset = kw.get('charset','utf8'),
        autocommit = kw.get('autocommit',True),
        maxsize = kw.get('maxsize', 10),
        minsize = kw.get('minsize', 1),
        loop = loop
    )

@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
    global __pool
    with (yield from __pool) as conn:
        cur = yield from conn.cursor(aiomysql.DictCursor)
        yield from cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchall()
        yield from cur.close()
        logging.info('rows returned : %s' % len(rs))
        return rs

#@asyncio.coroutine 这个不应该是generator
def create_args_string(lenth):
    L = []
    for n in range(lenth):
        L.append('?')
    return ', '.join(L)

@asyncio.coroutine
def execute(sql, args):
    log(sql, args)
    with (yield from __pool) as conn:
        try:
            cur = yield from conn.cursor()
            #print('excute sql 111 >> ',sql)
            #print('excute sql 222 >> ',args)
            yield from cur.execute(sql.replace('?','%s'), args)
            affected = cur.rowcount()
            yield from cur.close()
        except Exception :
            raise Exception('execute error')
        return affected

class Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default
    
    def __str__(self):
        return '<%s, %s, %s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):
    '字符串'
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

class IntegerField(Field):
    '整数类型'
    def __init__(self, name=None, primary_key=False, default=None, ddl='INT'):
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):
    '布尔类型'
    def __init__(self, name=None, primary_key=False, default=None, ddl='TINYINT(1)'):
        super().__init__(name, ddl, primary_key, default)

class FloatField(Field):
    '浮点类型'
    def __init__(self, name=None, primary_key=False, default=None, ddl='FLOAT'):
        super().__init__(name, ddl, primary_key, default)

class TextField(Field):
    '文本类型'
    def __init__(self, name=None, primary_key=False, default=None, ddl='TEXT'):
        super().__init__(name, ddl, primary_key, default)

class ModelMetaclass(type):
     
    def __new__(cls, name, bases, attrs):
        #排除model本身
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        #获取table名称
        tableName = attrs.get('__table__', None) or name
        logging.info(' found model: %s (table: %s)' % (name, tableName))
        #获取所有的Field和主键名
        mappings = dict()
        fields = []
        primaryKey = None
        for k,v in attrs.items():
            #logging.info(' found mappings: %s ==> %s' % (k,v))
            if isinstance(v, Field):
                logging.info(' found mappings: %s ==> %s' % (k,v))
                mappings[k]=v
                if v.primary_key:
                    #找到主键
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError('Primary Key not found.')
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f:'`%s`' %f, fields))
        attrs['__mappings__'] = mappings#保存属性和列的映射关系
        attrs['__table__'] = tableName        
        attrs['__primary_key__'] = primaryKey#主属性键名
        attrs['__fields__'] = fields #除主属性外的属性名
        #构造默认的SELECT，INSERT，UPDATE 和 DELETE 语句
        #print('### primaryKey >> ', primaryKey)
        #print('### escaped_fields >>> ',', '.join(escaped_fields))
        #print('### create_args_string >>> ', create_args_string(len(escaped_fields)+1))
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields)+1))
        #print('insert name == >> %s' % attrs['__insert__'])
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)

class Model(dict, metaclass=ModelMetaclass):

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'"%key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s : %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    @classmethod
    @asyncio.coroutine
    def find(cls, pk):
        ' find object by primary key '
        rs = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    @classmethod
    @asyncio.coroutine
    def findAll(cls):
        ' find all object '
        rs = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [], None)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    @classmethod
    @asyncio.coroutine
    def findNumber(cls, pk):
        pass

    @asyncio.coroutine
    def save(self):
        ' save data into db'
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__insert__, args)
        if rows != 1:
            logging.warning('failed to insert record: affected rows: %s' % rows)

    @asyncio.coroutine
    def update(self):
        ' update data into db'
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = yield from execute(self.__update__, args)
        if rows != 1:
            logging.warning('failed to update record: affected rows: %s' % rows)

    @asyncio.coroutine
    def delete(self):
        ' delete data from db'
        args = list(map(self.getValueOrDefault, self.__fields__))
        #args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__delete__, args)
        if rows != 1:
            logging.warning('failed to delete record: affected rows: %s' % rows)
