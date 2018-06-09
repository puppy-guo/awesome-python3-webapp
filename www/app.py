#!usr/env/bin python3
#-*- coding:utf-8 -*-

from orm_app import Model, IntegerField, StringField, create_pool, create_database
import asyncio

#数据库参数
database = {
'user':'root',
'password':'password',
'db':'aswsome'
}

class User(Model):
    __table__ = 'users'
    id = IntegerField('id', primary_key=True)
    name = StringField('user name')

async def main(loop):    
    #数据库初始化
    await create_pool(loop, **database)
    #创建实例
    user = User()
    user.id = 123
    user.name = 'puppy_guo'
    #创建数据表

    #存入数据库
    await user.save()
    return user.name

if __name__ == '__main__':

    #创建数据库
    if False == create_database(**database):
        raise Exception('create database fail..')
 
    loop = asyncio.get_event_loop()
    #loop.run_until_complete(init(loop))
    #loop.run_forever()

    task = asyncio.ensure_future(main(loop))
    res = loop.run_until_complete(task)
    print(res)

