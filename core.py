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


string_to_int: Callable[[Any], int] = lambda string: int(string.replace(',', ''))
string_to_float: Callable[[Any], float] = lambda string: float(string.strip('m ').replace(',', ''))

avg = lambda s: sum(s) / len(s)

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
