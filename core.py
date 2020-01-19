# -*- coding: utf-8 -*-

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
        self.verbose_idx = 4  # 0: show all; 6: show nothing

    def verbose(self, message: str, *args, **kwargs):
        level = kwargs.pop('level') if 'level' in kwargs else self.verbose_idx
        if level >= self.verbose_idx:
            return
        self.print(message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        if self.debug_bool:
            self.print(message, *args, **kwargs)

    def print(self, message='', *args, **kwargs):
        if args and kwargs:
            print(message, *args, **kwargs)
        elif args:
            print(message, *args)
        elif kwargs:
            print(message, **kwargs)
        else:
            print(message)

    def empty_line(self):
        print()

    def title(self, title):
        print(f"\n#{title.upper()}")

    def end(self, new_lines=1):
        print('\n' * new_lines)

    def keyval(self, key, val):
        print(f'\n#{key.upper()}: {val}\n')


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

    def insert_into(self, table, columns, values='', raw=''):
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

    def __init__(self, date_obj: date = None):
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

        #       date_obj must be a datetime object at this point.
        self.date_obj = date_obj

    def to_short_ISO(self):
        return datetime.strftime(self.date_obj, '%Y-%m-%d')

    def to_short_french_date(self):
        return datetime.strftime(self.date_obj, '%d-%m-%Y')

    def to_short_french_datetime(self):
        return datetime.strftime(self.date_obj, '%d-%m-%Y %H:%M')

    def to_short_french_date_but_whole_month(self):
        return datetime.strftime(self.date_obj, '%d %B %Y').lstrip('0')

    def to_slashed_french_date(self):
        return datetime.strftime(self.date_obj, '%d/%m/%Y').lstrip('0')

    def to_short_french_datetime_with_weekday(self):
        return datetime.strftime(self.date_obj, '%a %d-%m-%Y %H:%M')

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

    def add_days(self, days=1):
        self.date_obj += timedelta(days=days)

    def add_one_day(self):
        self.add_days(1)

    def set_time(self, hour: int, minute: int = 0):
        self.date_obj = self.date_obj.replace(hour=hour, minute=minute)

    def to_date(self):
        return self.date_obj

    def get_weekday(self, fmt='short'):
        rtn = None
        if fmt not in ('short', 'long', 'int'):
            fmt = 'short'
        if fmt == 'short':
            rtn = datetime.strftime(self.date_obj, '%a')
        elif fmt == 'long':
            rtn = datetime.strftime(self.date_obj, '%A')
        elif fmt == 'int':
            rtn = int(datetime.strftime(self.date_obj, '%w'))
            if rtn == 0:
                rtn = 7
        return rtn

    def get_year(self):
        return self.date_obj.year

    def get_hour(self):
        return self.date_obj.hour

    def from_short_french_date(self, string):
        if not self.short_french_re.search(string):
            raise AttributeError
        return datetime.strptime(self.date_obj, '%d-%m-%Y')

    def from_long_french_datetime(self, string):
        # locale.setlocale(locale.LC_TIME, "French_France.1252")
        if not self.large_french_date_fmt_re.search(string):
            raise AttributeError
        self.date_obj = datetime.strptime(string, "%A %d %B %Y à %H:%M")

    def from_long_iso(self, string):
        if not self.large_iso_re.search(string):
            raise AttributeError
        self.date_obj = datetime.strptime(string, "%Y-%m-%d %H:%M:%S")

    def to_short_param(self):
        return datetime.strftime(self.date_obj, '%Y%m%d')

    def to_format(self, fmt):
        return datetime.strftime(self.date_obj, fmt)


class FrequenceDict:
    def __init__(self):
        self.data = {}

    def __getitem__(self, item):
        if item in self.data:
            return self.data[item]
        else:
            return None

    def __len__(self):
        return len(self.data)

    def __str__(self):
        return f"{self.data}"

    def __contains__(self, item):
        return item in self.data

    def add(self, elem):
        if elem in self.data:
            self.data[elem] += 1
        else:
            self.data[elem] = 1
        return True

    def items(self):
        return self.data.items()

    def get(self, elem):
        if elem in self.data:
            return self.data[elem]
        return None

    def keys(self, sort=True):
        if sort:
            return tuple(sorted(self.data.keys()))
        else:
            return tuple(self.data.keys())

    def keys_sorted_by_values(self):
        self.sort()
        return self.data.keys()

    def key_index(self, elem):
        self.sort()
        return list(self.data.keys()).index(elem)

    def remove(self, elem):
        if elem in self.data:
            if self.data[elem] == 1:
                del self.data[elem]
            else:
                self.data[elem] -= 1
            return True
        return False

    def reset(self, elem):
        self.data[elem] = 0

    def set(self, key, value: int):
        if value:
            self.data[key] = value
            return True
        return False

    def size(self):
        return self.__len__()

    def sort(self):
        self.data = self.sort_by_values()

    def sort_by_values(self, descending=True):
        items = sorted(self.data.items(), key=lambda x: x[1], reverse=descending)
        return dict(items)

    def unique_values(self):
        return tuple(set(self.data.values()))

    def values(self, sort=True):
        if sort:
            return tuple(sorted(self.data.values()))
        else:
            return tuple(self.data.values())
    def max(self):
        return max(self.data.values())

    def min(self):
        return min(self.data.values())


def frequence(seq):
    freq_dict = FrequenceDict()
    for elem in seq:
        freq_dict.add(elem)

    frequences = {}
    for key in freq_dict.keys(False):
        appearances = freq_dict[key]
        t = tuple([appearances[i] - appearances[i + 1] for i in range(len(appearances[:-1]))])
        frequences[key] = {
            'freq': t,
            'max': max(t),
            'min': min(t),
            'avg': sum(t) // len(t),
            'len': freq_dict[key],
            'seq': seq
        }

    return frequences


string_to_int: Callable[[Any], int] = lambda string: int(string.replace(',', ''))
string_to_float: Callable[[Any], float] = lambda string: float(string.strip('m ').replace(',', ''))

avg = lambda s: sum(s) / len(s)


def clean_number(string):
    if not string.rstrip('%s' % _currency).rstrip(' €£').replace(',', '').replace(' ', '').isdigit():
        return 0
    string = string.rstrip(' €£').replace(' ', '')
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


def clean_url(string, keep='trailing'):
    if not string:
        return string
    items = string.split('/')
    if keep == 'trailing':
        return items[-1]


def data_a_objecte(data='viernes 1 de enero de 2010'):
    """Date string to Datetime object"""
    dt = datetime.strptime(re.search(r'^(\w+ \d{1,2} de \w+ de 20\d{2})$', data).group(1), "%A %d de %B de %Y")
    return dt


def sort_dict_by_values(d, descending=True):
    items = sorted(d.items(), key=lambda x: x[1], reverse=descending)
    return dict(items)


class Internationalization:

    locale_dict = {
        'English': 'English_United Kingdom.1252',
        'French': 'French_France.1252',
        'Catalan': 'Catalan_Andorra.UTF8',
        'Spanish': 'Spanish_Spain.1252'
    }

    def __init__(self):
        self.default = self.locale_dict['French']

    def set_local_time(self, key):
        locale.setlocale(locale.LC_TIME, self.locale_dict[key])

    def set_local_monetary(self, key):
        locale.setlocale(locale.LC_MONETARY, self.locale_dict[key])

    def set_local_numeric(self, key):
        locale.setlocale(locale.LC_NUMERIC, self.locale_dict[key])

    def init(self):
        self.set_local_time('French')
        self.set_local_numeric('Spanish')
        self.set_local_monetary('Catalan')

_currency = locale.localeconv()['currency_symbol']
_display = Display()
_locale = Internationalization()
_locale.init()