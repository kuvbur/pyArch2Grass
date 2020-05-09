# -*- coding: utf-8 -*-
"""
Created on Thu May  7 19:53:16 2020

@author: da-rogojin
"""
from lxml import etree

fname = "test.ghx"
parser = etree.XMLParser(strip_cdata=False)
root = etree.parse(fname, parser)

#Добираемся до ветки с определением контейнеров
croot = root.xpath('//chunk[@name="DefinitionObjects"]/chunks//chunk[@name="Container"]')

#Проходим по контейнерам и заполняем словарь с именами параметров
param_name_dic={}
#Ищем группы
for chunk in croot:
    items = chunk.find('items')
    for item in items.getchildren():
        if item.get('name')=="Name" and item.text=="Group":
            #Получаем имя группы, т.е. имя группы свойств
            nickname = items.xpath('item[@name="NickName"]')[0].text
            #Пройдём по ID и поищем среди них ноды TEXT
            #Их содержание даст нам имя свойства
            id = items.xpath('item[@name="ID"]')
            for i in id:
                find_str = '//item[@name="InstanceGuid" and text()="'+i.text+'"]'
                item_by_id = items.xpath(find_str)
                #Среди них поищем text
                for it in item_by_id:
                    for item in it.getparent():
                        if item.get('name')=="Name" and item.text=="Text":
                            param_name = it.getparent().xpath('item[@name="NickName"]')[0].text
                            #Запишем в словарь имя, чтоб потом по guid его найти
                            full_name = "Property:"+nickname+"/"+param_name
                            param_name_dic[i.text]={'Group':nickname, 'Name':param_name, 'FullName':full_name}
print(param_name_dic)