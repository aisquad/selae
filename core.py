import locale
import pymysql
import re
import requests

from bs4 import BeautifulSoup
from typing import Any, Callable
from datetime import datetime


class SQL:
    def __init__(self):
        self.connection: pymysql.connect = None
        self.cursor: pymysql.cursors.Cursor = None

    def set_connection(self, cfg_dict):
        cfg_dict['cursorclass'] = pymysql.cursors.DictCursor
        self.connection = pymysql.connect(**cfg_dict)
        self.cursor = self.connection.cursor

    def get_resultset(self, sql):
        with self.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
        i = 1
        j = len(result)

        for rs in result:
            yield rs, i, j
            i += 1

    def get_table_keys(self, table, key_name):
        sql = "SELECT %s  FROM %s" % (key_name, table)
        list = []
        for rs in self.get_resultset(sql):
            list.append(rs[0][key_name])
        return list

    def set_insert_to_sql(self, table, columns, values):
        value_str = ''
        for v in values:
            if isinstance(v, str):
                value_str += "'%s', " % v
            else:
                value_str += "%s, " % v
        value_str = value_str.strip(', ')
        sql = "INSERT INTO %s (%s) VALUES (%s);" % (table, ', '.join(columns), value_str)
        print(sql)
        return sql

    def insert_into(self, table, columns, values):
        with self.cursor() as cursor:
            sql = self.set_insert_to_sql(table, columns, values)
            cursor.execute(sql)
            result = cursor.fetchall()
        return result

    def match(self, table, where):
        with self.cursor() as cursor:
            sql = f"SELECT * FROM {table} WHERE {where};"
            cursor.execute(sql)
            result = cursor.fetchall()
        return result

    def connected(self):
        return self.conection != False

    def close(self):
        self.connection.close()


class Browser:
    def __init__(self):
        self.visited_pages = 0

    def _get_page_content(self, url):
        self.visited_pages += 1
        return requests.get(url).content

    def parse_html(self, url):
        soup = BeautifulSoup(self._get_page_content(url), "html.parser")
        return soup


string_to_int: Callable[[Any], int] = lambda string: int(string.replace(',', ''))
string_to_float: Callable[[Any], float] = lambda string: float(string.strip('m ').replace(',', ''))

avg = lambda s: sum(s) / len(s)

def clean_number(string):
    if not string.strip(' %s' % _currency).isdigit():
        return 0
    return locale.atof(string.strip(' %s' % _currency))

def old_clean_number(string):
    if not string.strip('€').isdigit():
        return 0
    string = string.rstrip(" €").replace('.', '')
    if ',' in string:
        return float(string.replace(',', '.'))
    else:
        return int(string)


def data_a_objecte(data='viernes 1 de enero de 2010'):
    """Date string to Datetime object"""
    dt = datetime.strptime(re.search(r'^(\w+ \d{1,2} de \w+ de 20\d{2})$', data).group(1), "%A %d de %B de %Y")
    return dt


locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
locale.setlocale(locale.LC_MONETARY, 'Catalan_Andorra.UTF8')
_currency = locale.localeconv()['currency_symbol']
