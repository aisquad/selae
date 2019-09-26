#!python3
import locale
import pickle
import re

from argparse import ArgumentParser
from datetime import datetime, date, timedelta
from typing import Pattern

from core import avg, BeautifulSoup, Browser, clean_number, data_a_objecte, Display


class TinyStats:
    def __init__(self):
        pass

    def get_consecutives(self, numbers):
        if not numbers:
            return []
        numbers = list(numbers)
        numbers.sort()
        temp = [numbers[i + 1] - numbers[i] for i in range(4)]
        consecutives = []
        if sum(temp) == 4:
            return [tuple(numbers)]
        elif sum(temp[:-1]) == 3:
            return [tuple(numbers[:4])]
        elif sum(temp[1:]) == 3:
            return [tuple(numbers[1:])]
        elif sum(temp[:2]) == 2:
            consecutives.append(tuple(numbers[:3]))
            numbers = numbers[3:]
        elif sum(temp[1:3]) == 2:
            consecutives.append(tuple(numbers[1:4]))
            numbers = []
        elif sum(temp[2:]) == 2:
            consecutives.append(tuple(numbers[2:]))
            numbers = numbers[:2]
        if numbers:
            length = len(numbers) - 1
            if length:
                for e in [(numbers[i], numbers[i + 1]) for i in range(length) if numbers[i + 1] - numbers[i] == 1]:
                    consecutives.append(e)
        return consecutives

    def get_consecutives_by_length(self, numbers):
        lengths = []
        consec = self.get_consecutives(numbers)
        for items in consec:
            lengths.append(len(items))
        return lengths

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
        display.print ("#URL", url)
        html = self._browser.parse_html(url)
        self.links = html.find('div', {'class': 'contenedorEnlaces'})
        self.html = html.find('div', {'class': 'contenidoRegion'})

    def save(self):
        if len(self.data)<1:
            raise MemoryError('No data to save')
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
        self.alreadyseen = []
        self.steps = []
        self.previous_draw = ''
        self.next_draw = ''
        self.href = ''

        self.updated = datetime.now()

class EuromilionsDraw(Draw):
    def __init__(self):
        Draw.__init__(self)

    def delays(self):
        n = list(self.numbers)
        n.sort()
        s = tuple([n[i + 1] - n[i] for i in range(0, 4)])
        return {'numbers': n, 'steps': s, 'max': max(s), 'min': min(s), 'avg': avg(s), 'sum': sum(s)}

    def __str__(self):
        return f"""
        Data: {self.datetime:%Y/%m/%d}
        Nombres: {self.numbers}
        Estrelles: {self.special_numbers}
        Consecutives: {self.consecutives}
        Repeated Unities: {self.repeated_unities}
        Repeated Dozens: {self.repeated_dozens}
        Repeated Numbers: {self.alreadyseen}
        Dozens: {self.dozens}
        href: {self.href}
        prev: {self.previous_draw}
        next: {self.next_draw}
        """
        # Dades sorteig: {self.bets}
        # Premis: {self.prizes}


class ElGordo(Loterias):
    def __init__(self):
        Loterias.__init__(self)
        self.home += "/gordo-primitiva"


class Euromilions(Loterias):

    cat_re: Pattern[str] = re.compile(r'^(\d{1,2})ª \(?([1-5] \+ [0-2])\)?$')

    def __init__(self):
        Loterias.__init__(self)
        self.skip_header = '/es/euromillones/sorteos'
        self.home += '/euromillones'
        self._current_draw: EuromilionsDraw = None
        self.data_filename = 'euromillones.bin'
        self.numbers = range(1, 51)
        self.special_numbers = range(1,13)

    def get_home_content(self):
        self.current_content()
        last_result = self.html.find('a', {'id': 'lastResultsTitleLink'})
        last_result_link = last_result.get('href')
        self.last_result_link = last_result_link.replace(self.skip_header, '')

    def get_draw(self, draw):
        self.fetch_draw_data(draw)

    def set_draw(self, draw_id=None):
        if not draw_id:
            self.data.setdefault(len(self.data), self._current_draw)
        else:
            self.data.update({draw_id: self._current_draw})

    def fetch_draw_data(self, draw):
        draw = draw.replace(self.skip_header, '')
        self.current_content("%s%s" % ('/sorteos', draw))
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

    def fetch_title(self, region: BeautifulSoup):
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
        h2_tag: BeautifulSoup = region.find('h2')
        if not h2_tag:
            h2_tag = region.find('h3')
        if not h2_tag:
            display.print (region)
        self._current_draw.datetime = datetime.strptime(
            re.search(
                r'Sorteo\xa0\d{1,3}, (\w+ \d{1,2} de \w+ de 20\d{2})$',
                h2_tag.text).group(1),
            "%A %d de %B de %Y"
        )

    def fetch_bets(self, region: BeautifulSoup):
        #items = [(re.search(r"^([^:\xa0]+):?[ \xa0]([\d,.]+)[ €]*$", p.text), '%r' % p.text) for p in region.find_all('p')]
        #display.print(items)
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
        self.set_draw()
        while self.prev_draw:
            display.print(self._current_draw)
            self.get_draw(self.prev_draw)
            self.set_draw()
        self.show()

    def walk(self):
        if len(self.data) == 0:
            self.load()
        i=0;j=0
        for key in self.data:
            draw: EuromilionsDraw = self.data[key]
            display.print(f"{key}.-{draw}")
            i+= len(draw.alreadyseen)
            j += len(draw.consecutives)
        display.print(len(self.data))
        display.print("repeated", i, (  i*100)/len(self.data))
        display.print("consecutives", j, (j*100)/len(self.data))
        self.show()

    def walk_steps(self):
        self.load()
        k = 0
        t='\t'
        for key in self.data:
            draw: EuromilionsDraw = self.data[key]
            steps = draw.delays()
            numbers = list(draw.numbers)
            numbers.sort()
            if 50 > steps['sum'] > 0:
                display.print(
                    f"{draw.datetime:%Y/%m/%d}\t{t.join('%s' % n for n in numbers)}\t{draw.dozens}\t{steps['sum']}"
                )
                k += 1
                display.print("delay:", k)

    def show(self):
        s = SelectNextDrawWeekDay()
        next_draw = datetime.strftime(s.run(), "%a %Y/%m/%d")
        display.print(
            f"""
            VISITED PAGES: {self.visited_pages}
            INIT TIME: {self.init_time:%Y/%m/%d %H:%M:%S}
            CUR TIME: {datetime.now():%Y/%m/%d %H:%M:%S}
            NEXT DRAW: {next_draw}
            """
        )

    def get_more_url(self):
        data = data_a_objecte('viernes 24 de diciembre de 2010')
        j = 1
        for i in range(7482, 4969, -7):
            url = f"/{data:%Y}/{i}02001"
            #display.print(f"{j: >3} {url} {data:%Y/%m/%d}")
            data = data - timedelta(days=7)
            j += 1
            yield url

    def get_new_draw_id(self):
        return len(self.data)+1

    def dont_stop(self):
        for url in game.get_more_url():
            self.get_draw(url)
            self.set_draw()
        self.save()
        self.show()

    def fix_links(self):
        """
        Els enllaços a partir del 2010/12/31 no estan bé al web i no són accessibles.
        Amb el mètode get_more_url() superem este inconvenient, però els enllaços que es
        desen automàticament són erronis.

        Recorrem de nou els sortejos i els deixem els enllaços correctes.
        """
        for draw_id in range(360, 0, -1):
            draw = self.data[draw_id]
            draw.next_draw = self.data[draw_id+1].href
            draw.previous_draw = self.data[draw_id-1].href if self.data.get(draw_id-1) else ''

    def reverse_indexes(self):
        aux = {}
        for k in reversed(sorted(self.data.keys())):
            i = len(aux) + 1
            display.print(k, '->', i, self.data[k])
            aux.setdefault(i, self.data[k])
        self.data = aux

    def fix_draw(self, draw_id=291):
        # for draw_id in range(48, 274):
        #     self.get_draw(self.data[draw_id].href, draw_id)
        self.get_draw(self.data[draw_id].href, draw_id)

    def fix(self):
        if len(self.data) == 0:
            self.load()
        for key in self.data:
            draw: EuromilionsDraw = self.data[key]
            draw.repeated_dozens = stats.get_repeated_tens(draw.numbers)
            display.print(f"{key}.-{draw}")

    def download_database(self):
        self.surf()
        self.dont_stop()
        self.reverse_indexes()
        self.fix_links()
        self.save()
        self.show()

    def update(self, save=False):
        """Become the update from the last draw."""
        self.load()
        last_draw_id = len(self.data)
        last_draw = self.data[last_draw_id]
        self.get_draw(last_draw.href if not last_draw.next_draw != '' else self.get_draw(last_draw.next_draw))
        self.set_draw(last_draw_id)
        if self.next_draw:
            while self.next_draw:
                self.get_draw(self.next_draw)
                self.set_draw(self.get_new_draw_id())

        if save:
            self.save()


class SelectNextDrawWeekDay:
    def __init__(self):
        self.today = date.today()
        self.weekday = self.today.weekday()
        self.now = datetime.now()

    def run(self):
        weekday = self.weekday
        date = self.today
        while (weekday not in (1, 4)):
            date = datetime(date.year, date.month, date.day) + timedelta(days=1)
            weekday = date.weekday()
        return date


if __name__ == '__main__':
    """-Uwn"""
    stats = TinyStats()
    game = Euromilions()
    display = Display()
    arg_parser = ArgumentParser()
    arg_parser.add_argument('-D', '--download', dest='dl_adb', action='store_true')
    arg_parser.add_argument('-l', '--load', dest='load', action='store_true')
    arg_parser.add_argument('-n', '--nextdraw', dest='nextdraw', action='store_true')
    arg_parser.add_argument('-w', '--walk', dest='walk', action='store_true')
    arg_parser.add_argument('-W', '--walksteps', dest='walksteps', action='store_true')
    arg_parser.add_argument('-U', '--update', dest='update', action='store_true')
    arg_parser.add_argument('-S', '--save', dest='save', action='store_true', default=False)
    args = arg_parser.parse_args()
    if args.dl_adb:
        game.download_database()
    if args.load:
        game.load()
    if args.update:
        game.update(args.save)
    if args.walk:
        game.walk()
    if args.walksteps:
        game.walk_steps()
    if args.nextdraw:
        s = SelectNextDrawWeekDay()
        locale.setlocale(locale.LC_ALL, "Catalan_Spain.1252")
        next_draw = datetime.strftime(s.run(), "%a %d/%m/%y")
        display.print(f"{'': >12}dia del següent sorteig: ", next_draw)
        locale.setlocale(locale.LC_ALL, "Spanish_Spain.1252")
