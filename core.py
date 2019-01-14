import locale
import os
import pickle
import re
import requests

from bs4 import BeautifulSoup
from typing import Any, Callable
from datetime import datetime


class Browser:
    def __init__(self):
        self.visited_pages = 0

    def _get_page_content(self, url):
        self.visited_pages += 1
        return requests.get(url).content

    def parse_html(self, url):
        soup = BeautifulSoup(self._get_page_content(url), "html.parser")
        return soup


class County:
    def __init__(self):
        self.id = 0
        self.name = ''
        self.href = ''
        self.type = ''
        self.updated = None

    def __str__(self):
        return f"""
        ID: {self.id}
        nom: {self.name}
        tipus: {self.type}
        href: {self.href}
        """


class Town:
    def __init__(self):
        self.id = 0
        self.name = ''
        self.population = 0
        self.male_pop = 0
        self.female_pop = 0
        self.latitude = 0
        self.longitude = 0
        self.altitude = 0
        self.zipcode_ids = set()
        self.county = County()
        self.road_num = 0
        self.href = ''
        self.type = ''
        self.updated = None

    def __str__(self):
        zips = f"{len(self.zipcode_ids) and '[%i] ' % len(self.zipcode_ids) or ''}" \
               f"{', '.join(list(sorted(self.zipcode_ids)))}"
        return f"""
        ID: {self.id}
        Nom: {self.name}
        Població: {self.population}
        Població masculina: {self.male_pop}
        Població femenina: {self.female_pop}
        Latitud: {self.latitude}
        Longitud: {self.longitude}
        Altitud: {self.altitude}
        Nombre de vies: {self.road_num}
        Codi postal: {zips}
        Província: {self.county.name}
        Tipus: {self.type}
        Actualització: {self.updated:%Y/%m/%d %H:%M:%S}
        """


class ZipCode:
    def __init__(self):
        self.id = 0
        self.value = ''
        self.updated = None

    def __str__(self):
        return f"""
        ID: {self.id}
        Valor: {self.value}
        Actualització: {self.updated:%Y/%m/%d %H:%M:%S}
        """


class Road:
    def __init__(self):
        self.id = 0
        self.odonym = ''
        self.even = ''
        self.odd = ''
        self.nn = ''
        self.zipcode = ''
        self.town = Town()
        self.updated = None

    @property
    def name(self):
        return self.odonym

    def __str__(self):
        return f"""
        ID: {self.id}
        Nom: {self.odonym}
        Parells: {self.even}
        Imparells: {self.odd}
        Sense núm: {self.nn}
        Codi postal: {self.zipcode}
        Localitat: {self.town.name}
        Província: {self.town.county.name}
        Actualització: {self.updated:%Y/%m/%d %H:%M:%S}
        """


class EntitySet:
    def __init__(self, fn, attr=''):
        if not attr:
            attr = fn
        self.loaded = False
        self.fn = fn
        self.attr = attr
        self.data = []
        self.updated = None

    def __iter__(self):
        return iter(self.data)

    @property
    def size(self):
        return len(self.data)

    def as_dict(self):
        return dict([(item.id, item) for item in self.data])

    def append(self, element):
        self.data.append(element)

    def prepend(self, element):
        self.data.insert(0, element)

    def add(self, element):
        self.append(element)

    def get_town(self, element) -> Town:
        """
        Get element by name, if element type is a str
        or by id, if element type is an int.

        To ensure matches, element can be a 2-tuple string
        where first element is a town name and second one its county name.
        """
        if self.attr != 'towns':
            return False

        if isinstance(element, str):
            if element.startswith('href:'):
                element = element.replace('href:', '')
                for item in self.data:
                    if item.href == element:
                        return item
            elif element.startswith('re:'):
                element = element.replace('re:', '')
                elements = []
                for item in self.data:
                    if re.search(r"\b%s\b" % element, item.name, re.I | re.U):
                        elements.append(item)
                if len(elements) > 0:
                    if len(elements) > 1:
                        print("WARNING: There are more than one Town!",
                              ", ".join(["%s (%s)" % (element.name, element.county.name) for element in elements]))
                    return elements[0]
                print("UNKNOWN TOWN: %s" % element)
            else:
                elements = []
                for item in self.data:
                    if item.name == element:
                        elements.append(item)
                if len(elements) > 0:
                    if len(elements) > 1:
                        print("WARNING: There are more than one Town!",
                              ", ".join(["%s (%s)" % (element.name, element.county.name) for element in elements]))
                    return elements[0]
                print("UNKNOWN TOWN:", element)
        elif isinstance(element, tuple):
            town_name = element[0]
            county_name = element[1]
            for item in self.data:
                if item.name == town_name and item.county.name == county_name:
                    return item
        else:
            for item in self.data:
                if item.id == element:
                    return item
            print("UNKNOWN TOWN", element)
        return False

    def has_roads(self, zipcode):
        if self.attr != 'roads' or not isinstance(zipcode, ZipCode):
            return False

        zipcode = zipcode.value
        for road in self.data:
            if road.zipcode == zipcode:
                return True
        return False

    def get_county(self, item):
        if self.attr != 'counties':
            return False

        for county in self.data:
            if county.id == item:
                return county
        return False

    def update_town(self, target):
        if self.attr != 'towns':
            return False
        for town in self.data:
            if town.id == target.id:
                town = target
                town.updated = datetime.now()
                return True
        return False

class PostalCodesWeb:
    def __init__(self):
        self.home = ''
        self.prefix = ''
        self.html: BeautifulSoup = None
        self.browser = Browser()
        self.counties = EntitySet('counties')
        self.towns = EntitySet('towns')
        self.zipcodes = EntitySet('zipcodes')
        self.roads = EntitySet('roads')

    def current_content(self, page=''):
        url = "%s%s" % (self.home, page)
        self.html = self.browser.parse_html(url)

    def load(self, use_roads=False):
        dumps = (self.counties, self.towns, self.zipcodes)
        if use_roads:
            dumps = (self.counties, self.towns, self.zipcodes, self.roads)
        for item in dumps:
            fn = "%s_%s.bin" % (self.prefix, item.fn)
            if os.path.exists(fn):
                with open(fn, 'rb') as f:
                    obj = getattr(self, item.attr)
                    setattr(obj, 'data', pickle.load(f))
                item.loaded = True
            else:
                print(f"NO SUCH FILE / No es troba el fitxer {fn}")

    def save(self, data_set):
        for item in data_set:
            fn = "%s_%s.bin" % (self.prefix, item.fn)
            print(item, item.fn, item.size)
            if item.size > 0:
                with open(fn, 'wb') as f:
                    pickle.dump(item.data, f, pickle.HIGHEST_PROTOCOL)

    def save_all(self):
        data_set = (self.counties, self.towns, self.zipcodes, self.roads)
        self.save(data_set)

    def save_towns_and_roads(self):
        data_set = (self.towns, self.zipcodes)
        self.save(data_set)


string_to_int: Callable[[Any], int] = lambda string: int(string.replace(',', ''))
string_to_float: Callable[[Any], float] = lambda string: float(string.strip('m ').replace(',', ''))

def clean_number(string):
    if not string.strip('€').isdigit():
        return 0
    string = string.rstrip(" €").replace('.', '')
    if ',' in string:
        return float(string.replace(',', '.'))
    else:
        return int(string)


def data_a_objecte(data='viernes 1 de enero de 2010'):
    locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
    dt = datetime.strptime(re.search(r'^(\w+ \d{1,2} de \w+ de 20\d{2})$', data).group(1), "%A %d de %B de %Y")
    return dt
