import locale
import pymysql
import re
import requests

from bs4 import BeautifulSoup
from typing import Any, Callable
from datetime import datetime, date, timedelta

class Display:
    def __init__(self):
        self.debug_bool = False
        self.verbose_idx = 4 # 0: show all; 6: show nothing

    def verbose(self, message: str, *args, **kwargs):
        level = kwargs.pop('level') if 'level' in kwargs else self.verbose_idx
        if level >= self.verbose_idx:
            return
        self.print(message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        if self.debug:
            self.print(message, *args, **kwargs)

    def print(self, message, *args, **kwargs):
        if args and kwargs:
            print(message, *args, **kwargs)
        elif args:
            print(message, *args)
        elif kwargs:
            print(message, **kwargs)
        else:
            print(message)


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

    def get_column_names(self, table):
        sql = "SELECT * FROM %s LIMIT 0" % table
        cursor = self.cursor()
        cursor.execute(sql)
        return tuple([x[0] for x in cursor.description])

    def get_table_keys(self, table, key_name, keys=[]):
        if keys:
            keys.insert(0, key_name)
            keys = '`%s` ' % '`, `'.join(keys)
        else:
            keys = '`%s`' % key_name
        sql = "SELECT %s  FROM `%s`;" % (keys, table)
        _display.print(f"SQL: {sql}")
        list = []
        for rs in self.get_resultset(sql):
            list.append(rs[0][key_name])
        return list

    def set_insert_to_sql(self, table, columns, values, raw=''):
        value_str = ''
        if values:
            for v in values:
                if isinstance(v, str):
                    value_str += "'%s', " % v
                else:
                    value_str += "%s, " % v
            value_str = "(%s)" % value_str.strip(', ')
        if raw:
            value_str = raw
        sql = "INSERT INTO %s (%s) VALUES %s;" % (table, ', '.join(columns), value_str)
        _display.verbose("SQL:", sql, level=5)
        return sql

    def insert_into(self, table, columns, values='', raw= ''):
        if raw:
            values = ''
        with self.cursor() as cursor:
            sql = self.set_insert_to_sql(table, columns, values, raw)
            cursor.execute(sql)
            result = cursor.fetchall()
        return result

    def match(self, table, where):
        with self.cursor() as cursor:
            sql = f"SELECT * FROM {table} WHERE {where};"
            cursor.execute(sql)
            result = cursor.fetchall()
        return result

    def get_last_recordset(self, table, orderby):
        with self.cursor() as cursor:
            sql = f'SELECT * FROM {table} ORDER BY {orderby} LIMIT 1'
            cursor.execute(sql)
            result = cursor.fetchall()
        return result

    def create_or_replace(self, table, cols):
        sql = f'CREATE OR REPLACE TABLE {table} ({cols}) engin=InnoDB default charset utf8'

    def drop_table(self, table):
        sql = f'DROP TABLE {table}'
        with self.cursor() as cursor:
            cursor.execute(sql)

    def truncate_table(self, table):
        sql = f'TRUNCATE TABLE {table}'
        with self.cursor() as cursor:
            cursor.execute(sql)

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

class DateHandler:

    Ymd_re = re.compile(r'^\d{4}(?P<sep>[-/])\d{2}(?P=sep)\d{2}$')
    dmY_re = re.compile(r'^\d{2}(?P<sep>[-/])\d{2}(?P=sep)\d{4}$')
    large_french_date_fmt_re = re.compile(r'^\w+ \d{1,2} \w+ \d{4} +à \d{2}:\d{2}$')
    large_iso_re = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')
    short_french_re = re.compile(
        r"^(?:(?:3[01])-(?:0[13578]|1[02])-(?:200[4-9]|201\d)|"
        r"(?:30)-(?:0[469]|11)-(?:200[4-9]|201\d)|"
        r"29-02-(?:200[48]|201[26])|"
        r"(?:0[1-9]|1\d|2[1-8])-02-(?:200[4-9]|201\d)"
        r"(?:0[1-9]|1\d|2\d)-(?:0[1-9]|1[0-2])-(?:200[4-9]|201\d))$"
    )

    def __init__(self, date_obj: date=None):
        if not date_obj:
            date_obj = datetime.now()
        elif isinstance(date_obj, str):
            Ymd_search = self.Ymd_re.search(date_obj)
            dmY_search = self.dmY_re.search(date_obj)
            large_french_fmt = self.large_french_date_fmt_re.search(date_obj)
            if Ymd_search:
                date_obj = datetime.strptime(date_obj, f"%Y{Ymd_search.group('sep')}%m{Ymd_search.group('sep')}%d")
            elif dmY_search:
                date_obj = datetime.strptime(date_obj, f"%d{dmY_search.group('sep')}%m{dmY_search.group('sep')}%Y")
            elif large_french_fmt:
                date_obj = datetime.strptime(date_obj, "%A %d %B %Y  à %H:%M")
            elif self.large_iso_re.search(date_obj):
                date_obj = datetime.strptime(date_obj, '%Y-%m-%d %H:%M:%S')
        self.date_obj = date_obj

    def to_short_ISO(self):
        return datetime.strftime(self.date_obj, '%Y-%m-%d')

    def to_short_french(self):
        return datetime.strftime(self.date_obj, '%d-%m-%Y')

    def to_short_french_datetime(self):
        return datetime.strftime(self.date_obj, '%d-%m-%Y %H:%M')

    def substract_days(self, days):
        return self.date_obj - timedelta(days=days)

    def minus_one_day(self):
        self.substract_days(1)

    def days_ago(self, days):
        self.substract_days(days)

    def one_day_ago(self):
        self.substract_days(1)

    def yesterday(self):
        self.date_obj = date.today() - timedelta(days=1)

    def tomorrow(self):
        self.date_obj = date.today() + timedelta(days=1)

    def to_date(self):
        return self.date_obj

    def from_short_french(self, string):
        if not self.short_french_re.search(string):
            raise AttributeError
        return datetime.strptime(self.date_obj, '%d-%m-%Y')

    def from_large_french(self, string):
        #locale.setlocale(locale.LC_TIME, "French_France.1252")
        if not self.large_french_date_fmt_re.search(string):
            raise AttributeError
        self.date_obj = datetime.strptime(string, "%A %d %B %Y à %H:%M")

    def from_large_iso(self, string):
        if not self.large_iso_re.search(string):
            raise AttributeError
        self.date_obj = datetime.strptime(string, "%Y-%m-%d %H:%M:%S")

    def to_short_param(self):
        return datetime.strftime(self.date_obj, '%Y%m%d')

string_to_int: Callable[[Any], int] = lambda string: int(string.replace(',', ''))
string_to_float: Callable[[Any], float] = lambda string: float(string.strip('m ').replace(',', ''))

avg = lambda s: sum(s) / len(s)

def clean_number(string):
    if not string.rstrip('%s' % _currency).rstrip(' €£').replace(',', '').replace(' ','').isdigit():
        return 0
    string = string.rstrip(' €£').replace(' ','')
    if ',' in string:
        return locale.atof(string)
    else:
        return locale.atoi(string)

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



locale.setlocale(locale.LC_TIME, 'French_France.1252')
locale.setlocale(locale.LC_MONETARY, 'Catalan_Andorra.UTF8')
locale.setlocale(locale.LC_NUMERIC, 'Spanish_Spain.1252')
_currency = locale.localeconv()['currency_symbol']
_display = Display()
print ("")
