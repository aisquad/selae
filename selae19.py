import locale
import pickle
import re

from argparse import ArgumentParser
from datetime import datetime, timedelta
from typing import Pattern

from core import Browser, BeautifulSoup, clean_number, data_a_objecte


class TinyStats:
    def __init__(self):
        pass

    def get_consecutives(self, numbers):
        if not numbers:
            return []
        numbers = list(numbers)
        numbers.sort()
        consecutives = []

        if numbers[4] - numbers[3] + numbers[3] - numbers[2] + numbers[2] - numbers[1] + numbers[1] - numbers[0] == 4:
            consecutives = [tuple(numbers)]
        else:
            if numbers[3] - numbers[2] + numbers[2] - numbers[1] + numbers[1] - numbers[0] == 3:
                consecutives.append((numbers[0], numbers[1], numbers[2], numbers[3]))
            elif numbers[4] - numbers[3] + numbers[3] - numbers[2] + numbers[2] - numbers[1] == 3:
                consecutives.append((numbers[0], numbers[1], numbers[2], numbers[3]))

            if not consecutives:
                for i in range(len(numbers) - 2):
                    if numbers[i + 2] - numbers[i + 1] + numbers[i + 1] - numbers[i] == 2:
                        consecutives.append((numbers[i], numbers[i + 1], numbers[i + 2]))

                for c in range(len(consecutives)):
                    for n in consecutives[c]:
                        numbers.remove(n)

            if len(numbers) >= 3:
                for i in range(len(numbers) - 1):
                    if numbers[i + 1] - numbers[i] == 1:
                        consecutives.append((numbers[i], numbers[i + 1]))
            if len(numbers) == 2 and numbers[1] - numbers[0] == 1:
                consecutives.append((numbers[0], numbers[1]))
        return consecutives

    def get_repeated_unities(self, numbers):
        repeated = []
        for unity in range(10):
            indexes = [numbers.index(u) for u in numbers if u % 10 == unity]
            if len(indexes) > 1:
                t = []
                for i in indexes:
                    t.append(numbers[i])
                repeated.append(tuple(t))
        return repeated

    def get_repeated_tens(self, numbers):
        repeated = []
        for dozen in range(10):
            indexes = [numbers.index(u) for u in numbers if u // 10 == dozen]
            if len(indexes) > 1:
                t = []
                for i in indexes:
                    t.append(numbers[i])
                repeated.append(tuple(t))
        return repeated

    def get_dozens(self, numbers):
        dozens = [0, 0, 0, 0, 0]
        for n in numbers:
            dozens[self.get_dozen(n)] += 1
        return "".join([str(d) for d in dozens])

    def get_dozen(self, i):
        return i//10 if i < 50 else 4


class Loterias:
    def __init__(self):
        self._browser = Browser()
        self.home = "https://www.loteriasyapuestas.es/es"
        self.html: BeautifulSoup = None
        self.links: BeautifulSoup = None
        self.last_result_link = ''
        self.visited_pages = 0
        self.init_time = datetime.now()
        self.prev_draw = None
        self.next_draw = None
        self.data = {}
        self.data_filename = ''

    def current_content(self, page=''):
        self.visited_pages += 1
        url = "%s%s" % (self.home, page)
        print ("#URL", url)
        html = self._browser.parse_html(url)
        self.links = html.find('div', {'class': 'contenedorEnlaces'})
        self.html = html.find('div', {'class': 'contenidoRegion'})

    def save(self):
        with open(self.data_filename, 'wb') as f:
            pickle.dump(self.data, f, pickle.HIGHEST_PROTOCOL)

    def load(self):
        with open(self.data_filename, 'rb') as f:
            self.data = pickle.load(f)


class Draw:
    def __init__(self):
        self.datetime: datetime = None
        self.bets = {}
        self.prizes = {}
        self.numbers = tuple()
        self.special_numbers = tuple()
        self.dozens = ''
        self.repeated_unities = []
        self.repeated_dozens = []
        self.consecutives = []
        self.previous_draw = ''
        self.next_draw = ''
        self.href = ''

        self.updated = datetime.now()

class EuromilionsDraw(Draw):
    def __init__(self):
        Draw.__init__(self)

    def __str__(self):
        return f"""
        Data: {self.datetime:%Y/%m/%d}
        Nombres: {self.numbers}
        Estrelles: {self.special_numbers}
        Consecutives: {self.consecutives}
        Repeated Unities: {self.repeated_unities}
        Repeated Dozens: {self.repeated_dozens}
        Dozens: {self.dozens}
        href: {self.href}
        prev: {self.previous_draw}
        next: {self.next_draw}
        """
        # Dades sorteig: {self.bets}
        # Premis: {self.prizes}
        # href: {self.href}


class Euromilions(Loterias):

    cat_re: Pattern[str] = re.compile(r'^(\d{1,2})ª \(?([1-5] \+ [0-2])\)?$')

    def __init__(self):
        Loterias.__init__(self)
        self.skip_header = '/es/euromillones'
        self.home += '/euromillones'
        self._current_draw: EuromilionsDraw = None
        self.data_filename = 'euromillones.bin'

    def get_home_content(self):
        self.current_content()
        last_result = self.html.find('a', {'id': 'lastResultsTitleLink'})
        last_result_link = last_result.get('href')
        self.last_result_link = last_result_link.replace(self.skip_header, '')

    def fetch_draw_data(self, draw):
        draw = draw.replace(self.skip_header, '')
        self.current_content(draw)
        regions = self.html.find_all('div', {'class': 'contenidoRegion'})
        self._current_draw = EuromilionsDraw()
        self._current_draw.href = draw
        for region in regions:
            if region.find('div', {'class': 'tituloRegion'}):
                self.fetch_title(region.find('div', {'class': 'tituloRegion'}))
                self.fetch_bets(region.find('div', {'class': 'cuerpoRegionSup'}))
                self.fetch_numbers(region.find('div', {'class': 'cuerpoRegionIzq'}))
                self.fetch_numbers(region.find('div', {'class': 'cuerpoRegionMed'}), True)
            elif region.find('table', {'class': 'tablaDetalle', 'summary': "Tabla detalle - Euromillones"}):
                self.fetch_statistics(
                    region.find('table', {'class': 'tablaDetalle', 'summary': "Tabla detalle - Euromillones"}))
            elif region.find('table', {'class': 'tablaDetalle millon'}):
                self.fetch_milion(region.find('table', {'class': 'tablaDetalle millon'}))

        numbers = self._current_draw.numbers
        self._current_draw.consecutives = stats.get_consecutives(numbers)
        self._current_draw.repeated_dozens = stats.get_repeated_tens(numbers)
        self._current_draw.repeated_unities = stats.get_repeated_unities(numbers)
        self._current_draw.dozens = stats.get_dozens(numbers)

        prev_draw_div = self.links.find('div', {'class': 'resultadoAnterior'})
        next_draw_div = self.links.find('div', {'class': 'resultadoSiguiente'})
        if prev_draw_div:
            href = prev_draw_div.find('a').get('href').replace(self.skip_header, '')
            self._current_draw.previous_draw = href
            self.prev_draw = href
        else:
            self.prev_draw = None
        if next_draw_div:
            href = next_draw_div.find('a').get('href').replace(self.skip_header, '')
            self._current_draw.next_draw = href
            self.next_draw = href
        else:
            self.next_draw = None
        self._current_draw.updated = datetime.now()

    def get_draw(self, draw, draw_id=None):
        self.fetch_draw_data(draw)

        if not draw_id:
            self.data.setdefault(len(self.data), self._current_draw)
        else:
            self.data.update({draw_id: self._current_draw})

    def fetch_title(self, region: BeautifulSoup):
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
        h2_tag: BeautifulSoup = region.find('h2')
        if not h2_tag:
            h2_tag = region.find('h3')
        if not h2_tag:
            print (region)
        self._current_draw.datetime = datetime.strptime(
            re.search(
                r'Sorteo\xa0\d{1,3}, (\w+ \d{1,2} de \w+ de 20\d{2})$',
                h2_tag.text).group(1),
            "%A %d de %B de %Y"
        )

    def fetch_bets(self, region: BeautifulSoup):
        #items = [(re.search(r"^([^:\xa0]+):?[ \xa0]([\d,.]+)[ €]*$", p.text), '%r' % p.text) for p in region.find_all('p')]
        #print(items)
        items = [re.search(r"^([^:\xa0]+):?[ \xa0]([\d,.]+)[ €]*$", p.text).groups() for p in region.find_all('p')]
        self._current_draw.bets = dict([(k,clean_number(v)) for k, v in items])

    def fetch_numbers(self, region: BeautifulSoup, special_numbers=False):
        ul_id = ('actMainNumbers', 'mainNumbers') if not special_numbers else ('actStars', 'stars')
        number_list = region.find('ul', {'id': ul_id[0]}) and len(region.find('ul', {'id': ul_id[0]}).find_all('li')) > 0 \
                      and region.find('ul', {'id': ul_id[0]}) or region.find('ul', {'id': ul_id[1]})
        number_list = [int(li.text) for li in number_list.find_all('li')]
        if not special_numbers:
            self._current_draw.numbers = tuple(number_list)
        else:
            self._current_draw.special_numbers = tuple(number_list)

    def fetch_statistics(self, region: BeautifulSoup):
        prizes = {}
        rows = [tr for tr in region.find_all('tr') if tr.find('td')]
        for row in rows:
            cells = [td.text for td in row.find_all('td')[:4]]
            cells[0] = re.sub(' +', ' ', cells[0])
            cat, hits = self.cat_re.search(cells[0]).groups()
            nat_win = clean_number(cells[1])
            prize = clean_number(cells[2])
            eur_win = clean_number(cells[3])
            prizes.setdefault(int(cat), (hits, prize, eur_win, nat_win))
        self._current_draw.prizes = prizes

    def fetch_milion(self, region):
        pass

    def surf(self):
        self.get_home_content()
        first_link = self.last_result_link
        self.get_draw(first_link)
        while self.prev_draw:
            print(self._current_draw)
            self.get_draw(self.prev_draw)
        self.show()

    def walk(self):
        if len(self.data) == 0:
            self.load()
        for key in self.data:
            draw: EuromilionsDraw= self.data[key]
            print (f"{key}.-{draw}")
        self.show()

    def show(self):
        print(
            f"""
            VISITED PAGES: {self.visited_pages}
            INIT TIME: {self.init_time:%Y/%m/%d %H:%M:%S}
            CUR TIME: {datetime.now():%Y/%m/%d %H:%M:%S}
            """
        )

    def get_more_url(self):
        data = data_a_objecte('viernes 24 de diciembre de 2010')
        j = 1
        for i in range(7482, 4969, -7):
            url = f"/sorteos/{data:%Y}/{i}02001"
            #print(f"{j: >3} {url} {data:%Y/%m/%d}")
            data = data - timedelta(days=7)
            j += 1
            yield url

    def dont_stop(self):
        for url in euromilions.get_more_url():
            self.get_draw(url)
        self.save()
        self.show()

    def reverse_indexes(self):
        aux = {}
        for k in reversed(sorted(self.data.keys())):
            i = len(aux) + 1
            print(k, '->', i, self.data[k])
            aux.setdefault(i, self.data[k])
        self.data = aux
        self.save()
        self.show()

    def fix_draw(self, draw_id=291):
        # for draw_id in range(48, 274):
        #     self.get_draw(self.data[draw_id].href, draw_id)
        self.get_draw(self.data[draw_id].href, draw_id)
        self.save()
        self.show()

    def fix(self):
        if len(self.data) == 0:
            self.load()
        for key in self.data:
            draw: EuromilionsDraw = self.data[key]
            draw.repeated_dozens = stats.get_repeated_tens(draw.numbers)
            print(f"{key}.-{draw}")
        self.save()
        self.show()

    def download_database(self):
        self.surf()
        self.dont_stop()
        self.reverse_indexes()
        self.save()
        self.show()

    def update(self, save=False):
        self.load()
        last_draw_id = len(self.data)
        last_draw = self.data[last_draw_id]
        has_next_link = last_draw.next_draw != ''
        if not has_next_link:
            self.get_draw(last_draw.href, last_draw_id)
            while self.next_draw:
                self.get_draw(self.next_draw)
        else:
            self.get_draw(last_draw.next_draw, 1180)
        if save:
            self.save()


if __name__ == '__main__':
    stats = TinyStats()
    euromilions = Euromilions()
    arg_parser = ArgumentParser()
    arg_parser.add_argument('-D', '--download', dest='dl_adb', action='store_true')
    arg_parser.add_argument('-w', '--walk', dest='walk', action='store_true')
    arg_parser.add_argument('-U', '--update', dest='update', action='store_true')
    arg_parser.add_argument('-S', '--save', dest='save', action='store_true', default=False)
    args = arg_parser.parse_args()
    if args.update:
        euromilions.update(args.save)
    if args.walk:
        euromilions.walk()
