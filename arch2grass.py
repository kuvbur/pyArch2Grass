from lxml import etree
import re
from sys import maxsize
from pprint import pprint

#Префиксы хэшей
PREFEXP = "pe"
PREFSTR = "ps"
PREFPROP = "pp"
#Список с регулярными выражениями и именами функций
#Порядок следования важен!
FUNCLIST=[
      ('[0-9a-z]*=[0-9a-zA-Z]*', 'EQ'),
      ('[0-9a-z]*<>[0-9a-zA-Z]*', 'NOTEQ'),
      ('OR\([0-9a-zA-Z,]+\)', 'OR'),
      ('AND\([0-9a-zA-Z,]+\)', 'AND'),
      ('IF\([0-9a-zA-Z,]+\)', 'IF'),
      ('IFS\([0-9a-zA-Z,]+\)', 'IFS'),
      ]

#Сколько аргументов у функции, тип данных на выходе
ARGLIST={
    'EQ':{
        'in':['Equal', 'Equal'],
        'in_qty' : 2,
        'split' : '='
        },
    'NOTEQ':{
        'in':['Equal', 'Equal'],
        'in_qty' : 2,
        'split' : '<>'
        },
    'OR':{
        'in':['Equal'],
        'in_qty' : 0,
        'split' : ','
        },    
    'AND':{
        'in':['Equal'],
        'in_qty' : 0,
        'split' : ','
        },    
    'IF':{
        'in':['Boolean', 'Equal_end', 'Equal_end'],
        'in_qty' : 3,
        'split' : ','
        },
    'IFS':{
        'in':['Boolean', 'Equal_end'],
        'in_qty' : 2,
        'split' : ','
        }}

def get_param(root):
    #Словарь 'e'+хэш : выражение
    expression_dic = {}
    #Словарь 'p'+хэш : имя параметра
    expression_dic['Property'] = {}
    #Словарь 's'+хэш : строка
    expression_dic['String'] = {}
    expression_dic['String']['psTRUE'] = 'TRUE'
    expression_dic['String']['psFALSE'] = 'FALSE'
    #Словарь с параметрами и их свойствах
    param_dic = {}
    param_dic['Классификация'] = {}
    param_dic['Системные'] = {}
    croot = root.xpath('//PropertyDefinitionGroups/*')
    for group in croot:
        group_name = group.xpath('Name')[0].text
        for param in group.xpath('PropertyDefinitions/*'):
            param_name = param.xpath('Name')[0].text
            param_type = param.xpath('DefaultValue/DefaultValueType')[0].text
            param_expression = []
            if param_type == 'Expression':
                for expr in param.xpath('DefaultValue/ExpressionDefaultValue/*'):
                    hash_exp =  PREFEXP + str(hash(expr.text) % ((maxsize + 1) * 2))
                    expression_dic[hash_exp] = expr.text
                    param_expression.append(hash_exp)
                    if '"' in expr.text:
                        string_list = re.findall('".*?"', expr.text)
                        for string in string_list:
                            hash_string =  PREFSTR + str(hash(string) % ((maxsize + 1) * 2))
                            expression_dic['String'][hash_string] = string
                    if '{Property' in expr.text:
                        property_list = re.findall('{.*?}', expr.text)
                        for p in property_list:
                            p = p.replace("{Property:","")
                            p = p.replace("}","")
                            p_full_name = p.split('/')
                            if len(p_full_name)>1:
                                p_group_name = p_full_name[0]
                                p_param_name = "".join(p_full_name[1:])
                            else:
                                p_group_name = ""
                                p_param_name = p
                            if p_group_name == 'Классификация':
                                param_dic['Классификация'][p_param_name] = p_param_name
                            elif len(p_group_name)<1:
                                param_dic['Системные'][p_param_name] = p_param_name
                            else:
                                param_dic[p] = {'Group':p_group_name, 'Name':p_param_name}
                            expression_dic['Property'][PREFPROP + str(hash(p) % ((maxsize + 1) * 2))] = p
            full_name = group_name+"/"+param_name
            expression_dic['Property'][PREFPROP + str(hash(full_name) % ((maxsize + 1) * 2))] = full_name
            param_dic[full_name] = {'Group':group_name, 'Name':param_name, 'Expression': param_expression, 'Type':param_type}
    return param_dic, expression_dic

def get_endpoint(exp, type_function):
    end_point = []
    in_arg = []
    in_type = ARGLIST[type_function]['in']
    qty_arg = ARGLIST[type_function]['in_qty']
    split_char = ARGLIST[type_function]['split']
    #Переделать бы это на regexp, но потом
    for clear_char in [type_function, '(', ')']:
        exp = exp.replace(clear_char, '')
    in_arg = exp.split(split_char)
    if qty_arg>0:
        assert(len(in_arg) == qty_arg)
    for i, arg in enumerate(in_arg):
        if qty_arg>0 and in_type[i].endswith('_end') and (arg.startswith(PREFSTR) or arg.startswith(PREFPROP)):
            end_point.append(arg)
    return end_point, in_arg

def replace_pattern(expression, func_to_replace, type_function):
    operations_dict = {}
    end_point = []
    has_func = True
    while has_func:
        exp_list = re.findall(func_to_replace, expression)
        has_func = len(exp_list)>0
        for exp in exp_list:
            hash_ =  type_function+str(hash(exp) % ((maxsize + 1) * 2))
            #Смотрим - что за функция на попалась и делим её на аргументы
            end_point_, in_arg = get_endpoint(exp, type_function)
            operations_dict[hash_] = {'In':in_arg, 'Type': type_function}
            end_point = end_point + end_point_
            expression = expression.replace(exp, hash_)
    return expression, operations_dict, end_point

def parse_expression(expression, expression_dic):
    operations_dict = {}
    end_point = []
    #Сохраним для истории певозданную формулу
    operations_dict['Clear'] = expression
    #Заменяем все строки, чтоб кавычки не мешали
    for hash_string, string in expression_dic['String'].items():
        expression = expression.replace(string, hash_string)
    #Заменяем все параметры
    for hash_pname, pname in expression_dic['Property'].items():
        expression = expression.replace("{Property:"+pname+"}", hash_pname)
    #Чистим пробелы, они нам уже не нужны
    expression = expression.replace(" ", "")
    #Последовательно сворачиваем выражение в словарь
    for func in FUNCLIST:
        func_to_replace, type_function = func
        expression, operations_dict_func, end_point_ = replace_pattern(expression, func_to_replace, type_function)
        end_point = end_point + end_point_
        operations_dict.update(operations_dict_func)
    #Конец клубка
    operations_dict['Start'] = expression
    operations_dict['End'] = end_point
    return operations_dict

def read_property(fname):
    parser = etree.XMLParser(strip_cdata=False)
    root = etree.parse(fname, parser).getroot()
    param_dic, expression_dic = get_param(root)
    operations_dict={}
    for hash_exp in expression_dic.keys():
        if hash_exp.startswith('pe'):
            expression = expression_dic[hash_exp]
            operations_dict[hash_exp] = parse_expression(expression, expression_dic)
    operations_dict['String'] = expression_dic['String']
    operations_dict['Property'] = expression_dic['Property']
    return param_dic, operations_dict

if __name__ == "__main__":
    fname = 'test_file/test.xml'
    param_dic_1, operations_dict_1 = read_property(fname)
    
    # fname = 'test_file/test2.xml'
    # param_dic_2, operations_dict_2 = read_property(fname)   
    

        

    
