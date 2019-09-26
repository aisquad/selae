"""
2019-09-22
Loterias y apuestas ha canviat la seua web, demanera que les dades són més difícils
d'obtindre per HTML ja que és el PHP els qui els proporciona per mitjà de JS de forma dinàmica.

He descobert una web francesa que conté totes les dades de totes les loteries que hi participen.

És a dir, això em permetrà rebre tota la informació no només d'Espanya sinò de França i altres paisos des dels inici,
amb dades reals, SELAE té molts errors encara (ni tan sols amb l'API per a obtenir dades via JSon són correctes).

He creat selaJSON per a obtenir les dades via els servei JSon, però les dades que s'obtenen estan incompletes, només
apareixen les boles ordenades de major a menor i les dades de sortejos antics seguixen sense estar bé.

Inspirat en la feina ja feta incorporaré totes les dades disponibles als objectes, en faré una amb totes les dades
i una reduida només amb dades rellevants:
BD completa:
- sortejos
- guanyadors per països
- premis per països

BD liviana:
- sortejos
- guanyadors totals
- premis totals

sortejos inclourà:
- id sorteig
- data sorteig
- data obtenció de dades
- sorteig següent i/o anterior
- boles en ordre d'aparició
- estreles en ordre d'aparició
- premi oferit
- recaptació
"""


import pickle
import re

from argparse import ArgumentParser
from datetime import datetime, date, timedelta
from typing import Pattern

from core import BeautifulSoup, Browser, clean_number, Display, DateHandler

class EuroMillionsDotCom():
    def __init__(self):
        self._browser = Browser()
        self.home = 'https://www.euro-millions.com/fr/'
        self.html: BeautifulSoup = None
        self.links: BeautifulSoup = None
        self.last_result_link = ''
        self.visited_pages = 0
        self.init_time = datetime.now()
        self.prev_draw = None
        self.next_draw = None
        self.data = []
        self.data_filename = ''

    def current_content(self, page=''):
        self.visited_pages += 1
        url = "%s%s" % (self.home, page)
        display.print ("#URL", url)
        html = self._browser.parse_html(url)
        self.links = html.find('div', {'class': 'contenedorEnlaces'})
        self.html = html.find('div', {'class': 'contenidoRegion'})

    def set_draw(self, draw_data, draw_id=None):
        if not draw_id:
            self.data.append(draw_data)
        else:
            if draw_id > len(self.data):
                raise IndexError
            self.data[draw_id] = draw_data
        return True

    def save(self):
        if len(self.data)<1:
            raise MemoryError('No data to save')
        with open(self.data_filename, 'wb') as f:
            pickle.dump(self.data, f, pickle.HIGHEST_PROTOCOL)
        return True

    def load(self):
        with open(self.data_filename, 'rb') as f:
            self.data = pickle.load(f)
        return True

class EuromillionsDraw:
    def __init__(self):
        self.balls: tuple = tuple()
        self.stars: tuple = tuple()
        self.jackpot: float = 0.0
        self.bets: int = 0
        self.prizes: dict = {}
        self.href: str = ''
        self.next_draw: EuromillionsDraw = None
        self.prev_draw: EuromillionsDraw = None
        self.date = DateHandler()
        self.created_date = DateHandler()
        self.modified_date = DateHandler()

    def sort_tuple(self, t):
        l = list(t)
        l.sort()
        return tuple(l)

    def sorted_balls(self):
        return self.sort_tuple(self.balls)

    def sorted_stars(self):
        return self.sort_tuple(self.stars)

    #LIGHT STATS
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

    def get_weight(self, numbers):
        l = list(numbers)
        l.sort()
        return l[-1]-l[0]

    def __str__(self):
        return f"""
    href: {self.href}
    id: {self.id}
    date: {self.date.to_short_french_datetime()}
    balls: {self.balls}
    stars: {self.stars}
    jackpot: {self.jackpot}
    bets: {self.bets}
    
    #TINY STATS
    sorted b.: {self.sorted_balls()}
    dozens: {self.get_dozens(self.balls)}
    rep. unit.: {self.get_repeated_unities(self.balls)}
    rep. tens: {self.get_repeated_tens(self.balls)}
    consec: {self.get_consecutives(self.balls)}
    weight: {self.get_weight(self.balls)}
    
    prev: {self.prev_draw}
    next: {self.next_draw}
    """


class EuroPrize:
    def __init__(self):
        self.cat: int = 0
        self.cat_text: str = ''
        self.winners: int = 0
        self.amount: float = 0.0
        self.monetary: str = 'EUR'
        self.amount_total: float = 0.0
        self.winners_total: int = 0

    def set_prize(self, prize):
        if not isinstance(prize, EuroPrize):
            raise TypeError(
                "No s'ha proporcionat un tipus de variable vàlid, s'esperava un objecte de la classe EuroPrize."
            )
        self.cat = prize.cat
        self.cat_text = prize.cat_text
        self.winners = prize.winners
        self.amount = prize.amount
        self.monetary = prize.monetary
        self.winners_total = prize.winners_total
        self.amount_total = prize.amount_total

    def __str__(self):
        return f"""
    cat: {self.cat}
    hits: {self.cat_text}
    winners: {self.winners}
    amount: {self.amount}
    eurowinners: {self.winners_total}
    euroamount: {self.amount_total}
    """

    def __repr__(self):
        return f"""
    cat: {self.cat}
    hits: {self.cat_text}
    winners: {self.winners}
    amount: {self.amount}
    eurowinners: {self.winners_total}
    euroamount: {self.amount_total}
    """


class Euromillions(EuroMillionsDotCom):

    cat_re = re.compile(r'(\d(?: \+ \d)?)(?: étoiles?)?')
    bet_re = re.compile(r"Pour ce tirage, on a dénombré ([\d ]+) participations")
    jackpot_re = re.compile(
        r"Le jackpot estimé vu à la publicité en espagne avant le tirage était de ([\d ]+) .\.", re.U
    )
    id_and_hour_re = re.compile(
        r"Le (?P<id>\d+)ème tirage EuroMillions a eu lieu le (?P<hour>.*?) et les numéros gagnants étaient:"
    )

    def __init__(self):
        EuroMillionsDotCom.__init__(self)
        self.home += 'resultats/'
        self.current_draw = EuromillionsDraw()
        self.data_filename = 'euromillions.bin'

    def surf(self, first, max_loops=0):
        self.next_draw = first
        loops = 0
        while self.next_draw:
            self.get_draw_page(self.next_draw)
            loops += 1
            if max_loops and loops > max_loops:
                break

    def walk(self):
        self.load()
        for draw in self.data:
            yield draw

    def fetch_items(self, container, item_name):
        return tuple([int(x.text) for x in container.find_all('li', {'class': item_name})])

    def get_draw_page(self, draw: str):
        self.current_draw = EuromillionsDraw()
        url = f"{self.home}{draw}"
        self.html = self._browser.parse_html(url)
        self.set_href(url)


        #Getting balls and stars
        topbox = self.html.find('div', {'class': 'topBox'})
        innerHTML = re.search(r'document\.getElementById\("jsBallOrderCell"\)\.innerHTML = "(.*?)";', topbox.text)
        if innerHTML:
            innerHTML = BeautifulSoup(innerHTML.group(1).replace(r'\"', '"'), 'html.parser')
            balls = self.fetch_items(innerHTML, 'new ball')
            stars = self.fetch_items(innerHTML, 'new lucky-star')
        elif topbox.find('div', id='jsBallOrderCell'):
            jsBallOrderCell = topbox.find('div', id='jsBallOrderCell')
            balls = self.fetch_items(jsBallOrderCell, 'new ball')
            stars = self.fetch_items(jsBallOrderCell, 'new lucky-star')
        else:
            raise NotImplemented('#Error: No balls found')
        self.set_balls(balls, stars)

        #Getting prizes
        winners = self.html.find_all('table', {'class': 'table breakdown mobFormat'})[0]
        foreigns_winners = self.html.find_all('div', {'class': 'prizeTableArea'})
        self.read_table(winners)
        for table in foreigns_winners:
            country = self.get_country(table.get('id'))
            self.read_table(table, country)

        #Getting bets, jackpot, id and date/hour
        found = 0
        for paragraph in self.html.find_all('p'):
            text = paragraph.text
            if self.bet_re.search(text):
                self.set_bets(self.bet_re.search(text).group(1))
                found += 1
            elif self.jackpot_re.search(text):
                self.set_jackpot(self.jackpot_re.search(text).group(1))
                found += 1
            elif self.id_and_hour_re.search(text):
                self.set_id_and_hour(self.id_and_hour_re.search(text).groups())
                found += 1
            if found == 3:
                break

        #Getting nav buttons
        prev_draw, next_draw = self.get_nav_buttons()
        self.set_navigation(prev_draw, next_draw)

        display.print(self.current_draw)
        self.set_draw(self.current_draw)
        self.visited_pages += 1

    def get_button(self, side='left'):
        button = self.html.find('div', {'class': f"prev-{side} print-off"})
        if button:
            button = self.clean_url(button.find('a').get('href'))
        return button

    def get_nav_buttons(self):
        prev_draw = self.get_button()
        next_draw = self.get_button("right")
        return prev_draw, next_draw

    def set_href(self, url):
        self.current_draw.href = url

    def set_balls(self, balls, stars):
        self.current_draw.balls = balls
        self.current_draw.stars = stars

    def set_navigation(self, prev, next):
        self.current_draw.prev_draw = prev
        self.current_draw.next_draw = next
        self.next_draw = next

    def clean_url(self, string, keep='trailing'):
        if not string:
            return string
        items = string.split('/')
        if keep == 'trailing':
            return items[-1]

    def set_bets(self, string):
        self.current_draw.bets = clean_number(string)

    def set_jackpot(self, string):
        self.current_draw.jackpot = clean_number(string)

    def set_id_and_hour(self, tuple):
        self.current_draw.id = clean_number(tuple[0])
        self.set_date(tuple[1])

    def set_date(self, date):
        date = date_handler(date)
        self.current_draw.date = date

    def get_country(self, id):
        id = id[-2:]
        if id in countries:
            id = id.lower()
        elif id == 'GB':
            id = 'uk'
        return id

    def read_table(self, table, country='es'):
        self.current_draw.prizes[country] = []
        rows = [tr for tr in table.find_all('tr') if tr.find('td')]
        cat = 1
        try:
            for row in rows:
                prize = EuroPrize()
                cells = [td.text for td in row.find_all('td')[:5]]
                if not self.cat_re.search(cells[0]): continue
                hits = self.cat_re.search(cells[0]).group(1)
                if '+' not in hits:
                    hits += ' + 0'
                prize.cat = cat
                prize.cat_text = hits
                prize.amount = clean_number(cells[1])
                prize.winners = clean_number(cells[2])
                prize.amount_total = clean_number(cells[3] if len(cells)>4 else '0')
                prize.winners_total = clean_number(cells[4] if len(cells)>4 else cells[3])
                self.current_draw.prizes[country].append(prize)
                cat += 1
        except IndexError:
            return

    def check_data(self):
        if len(self.data) == 0:
            self.load()

    def find_draw(self, targeted_draw, matches=4):
        balls = targeted_draw.balls
        draws = []
        for draw in self.data:
            if draw.id == targeted_draw.id:
                break
            hits = 0
            for ball in balls:
                if ball in draw.balls:
                    hits += 1
            if hits >= matches:
                draw.matches = hits
                draws.append(draw)
        return draws

    def find_all_draw_matches(self, matches=4):
        self.check_data()
        i = 0
        for draw in euromillions.data:
            draws = euromillions.find_draw(draw, matches)
            if len(draws) > 0:
                print(f'DRAW {draw.date.to_short_french()} {draw.balls} has got the following matches:')
                for dr in draws:
                    print('\t', dr.date.to_short_french(), dr.balls, dr.matches)
                i += 1
        print(i)


if __name__ == '__main__':

    display = Display()
    countries = ('UK', 'FR', 'ES', 'IE', 'PT', 'CH', 'BE', 'AT', 'LU')

    date_handler = DateHandler
    from_date = date_handler('2004/02/13').to_short_french()
    euromillions = Euromillions()
    #euromillions.find_all_draw_matches(4)
    euromillions.load()
    draw = euromillions.data[-7]
    print(draw)
    draws = euromillions.find_draw(draw, 4)
    for draw in draws:
        print(draw)
    print (euromillions.data[-8])
    print (f"DATE: {euromillions.data[-1].date.to_date():%Y/%m/%d}")




