# -*- coding: utf-8 -*-

"""
2019-09-22
Loterias y apuestas ha canviat la seua web, de manera que les dades són més difícils
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
from datetime import datetime
from itertools import combinations, product
from typing import Any, Callable, Union

from core import BeautifulSoup, Browser, DateHandler, Display, FrequenceDict, clean_number, clean_url, \
    Internationalization


class EuroMillionsDotCom():
    countries = ('UK', 'FR', 'ES', 'IE', 'PT', 'CH', 'BE', 'AT', 'LU')

    def __init__(self):
        self._browser: Browser = Browser()
        self.home = 'https://www.euro-millions.com/fr/'
        self.last_result_link = ''
        self.visited_pages = 0
        self.init_time = datetime.now()
        self.prev_draw = None
        self.next_draw = None
        self.data = []
        self.data_filename = ''
        self.is_loaded = False
        self.length = 0

    def set_draw(self, draw_data, draw_id=None):
        if not draw_id:
            self.data.append(draw_data)
        else:
            if draw_id > len(self.data):
                raise IndexError
            self.data[draw_id] = draw_data
        return True

    def save(self):
        if len(self.data) < 1:
            raise MemoryError('No data to save')
        with open(self.data_filename, 'wb') as f:
            pickle.dump(self.data, f, pickle.HIGHEST_PROTOCOL)
        return True

    def load(self):
        print("loading data...")
        with open(self.data_filename, 'rb') as f:
            self.data = pickle.load(f)
        print("data were loaded successfully!")
        self.is_loaded = True
        self.length = len(self.data)
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

    def get_year(self):
        return self.date.get_year()

    # LIGHT STATS
    def get_consecutives(self, numbers=None):
        if not numbers:
            numbers = self.balls
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

    def get_consecutives_by_length(self, numbers=None):
        if not numbers:
            numbers = self.balls
        lengths = []
        consec = self.get_consecutives(numbers)
        for items in consec:
            lengths.append(len(items))
        return lengths

    def get_repeated_unities(self, numbers=None):
        if not numbers:
            numbers = self.balls
        repeated = []
        for unity in range(10):
            indexes = [numbers.index(u) for u in numbers if u % 10 == unity]
            if len(indexes) > 1:
                t = []
                for i in indexes:
                    t.append(numbers[i])
                repeated.append(tuple(t))
        return repeated

    def get_repeated_tens(self, numbers=None):
        if not numbers:
            numbers = self.balls
        repeated = []
        for dozen in range(10):
            indexes = [numbers.index(u) for u in numbers if u // 10 == dozen]
            if len(indexes) > 1:
                t = []
                for i in indexes:
                    t.append(numbers[i])
                repeated.append(tuple(t))
        return repeated

    def get_dozens_old(self, numbers=None):
        """unused / deprecated"""
        if not numbers:
            numbers = self.balls
        dozens = [0, 0, 0, 0, 0]
        for n in numbers:
            dozens[self.get_dozen(n)] += 1
        return "".join([str(d) for d in dozens])

    def get_dozens(self, numbers=None):
        if not numbers:
            numbers = self.balls
        d = 0
        for n in numbers:
            if n == 50:
                # include number 50 into dozen 4.
                n = 49
            d += 10 ** (4 - (n // 10))
        return f'{d:0>5}'

    def get_units(self, numbers=None):
        if not numbers:
            numbers = self.balls
        u = 0
        for n in numbers:
            u += 10 ** (9 - (n % 10))
        return f'{u:0>10}'

    def get_dozen_group(self, dozens=None):
        if not dozens:
            dozens = self.get_dozens()
        group = ''
        group += '1' * dozens.count("1") if dozens.count('1') > 0 else ''
        group += '2' * dozens.count("2") if dozens.count('2') > 0 else ''
        group += '3' * dozens.count("3") if dozens.count('3') > 0 else ''
        group += '4' * dozens.count("4") if dozens.count('4') > 0 else ''
        group += '5' * dozens.count("5") if dozens.count('5') > 0 else ''
        return f'{group:>05}'

    def get_dozen(self, i):
        """unused / deprecated"""
        return i // 10 if i < 50 else 4

    def get_weight(self, numbers=None):
        if not numbers:
            numbers = self.balls
        l = list(numbers)
        l.sort()
        return l[-1] - l[0]

    def get_sum(self):
        return sum(self.balls)

    def get_holes(self):
        numbers = self.sorted_balls()
        return tuple([(numbers[i] - numbers[i - 1]) for i in range(1, 5)])

    def check_data(self) -> dict:
        test = {'jackpot': 0, 'nextdraw': 0}
        if self.jackpot == 0:
            display.print("jackpot is wrong")
            test['jackpot'] = -1
        if self.next_draw == None:
            display.print('next draw is wrong')
            test['nextdraw'] = -1
        return test

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
    dozens: {self.get_dozens()}
    rep. unit.: {self.get_repeated_unities()}
    rep. tens: {self.get_repeated_tens()}
    consec: {self.get_consecutives()}
    weight: {self.get_weight()}
    
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


class Page:
    def __init__(self):
        self.html: BeautifulSoup = None
        self.url: str = ''
        self._browser: Browser = Browser()
        self._container: BeautifulSoup = None

    def get_content(self, url):
        self.url = url
        self.html = self._browser.parse_html(url)

    def set_url(self, url):
        self.url = url

    def set_container(self, obj: BeautifulSoup):
        self._container = BeautifulSoup(obj, 'html.parser') if isinstance(obj, str) else obj

    def get_paragraphs(self):
        return self.html.find_all('p')


class EuroMillionPage(Page):
    def __init__(self):
        Page.__init__(self)

    def fetch_items(self, item_name):
        return tuple([int(x.text) for x in self._container.find_all('li', {'class': item_name})])

    def get_topbox_section(self):
        return self.html.find('div', {'class': 'topBox'})

    def get_first_table(self):
        return self.html.find_all('table', {'class': 'table breakdown mobFormat'})[0]

    def get_foreign_prize_table(self):
        return self.html.find_all('div', {'class': 'prizeTableArea'})

    def get_button(self, side='left'):
        button = self.html.find('div', {'class': f"prev-{side} print-off"})
        if button:
            button = clean_url(button.find('a').get('href'))
        return button

    def get_bets(self):
        bets = self.html.find('div', {'class': 'row figures'})
        numbers = []
        for bet in bets.find_all('div', {'class': 'box'}):
            text = bet.find('div', {'class': 'big'}).text
            if text.replace(' ', '').isdigit():
                numbers.append(int(text.replace(' ', '')))
        display.print(numbers)
        return numbers

    def get_nav_buttons(self):
        prev_draw = self.get_button()
        next_draw = self.get_button("right")
        return prev_draw, next_draw


class EuromillionsHistoryPage(Page):
    def __init__(self):
        Page.__init__(self)

    def get_all_archive_divs(self) -> BeautifulSoup:
        return self.html.find_all('div', {'class': 'archives'})

    def get_all_new_archive_links(self, last_draw_date) -> list:
        new_draws = []
        for div in self.get_all_archive_divs():
            a: BeautifulSoup = div.find('a', {'class': 'title'})
            cur_wday, cur_date = a.strings
            if cur_date == last_draw_date:
                break
            else:
                new_draws.append(clean_url(a.get('href')))
        return new_draws


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
        self.result_home = f'{self.home}resultats/'
        self.current_draw = EuromillionsDraw()
        self.data_filename = 'data/euromillions.bin'

    # READING LOCAL DATA
    def walk(self, reverse=False):
        self.check_data()
        copy = self.data.copy()
        if reverse:
            copy.reverse()

        for draw in copy:
            yield draw

    def get_last_draw(self) -> list:
        self.check_data()
        return self.data[-1]

    def get_draw(self, draw_id):
        self.check_data()
        for draw in self.walk(True):
            if draw.id == draw_id:
                return draw
        raise ValueError(f'DRAWID NOT FOUND: {draw_id}')

    def skip(self, draws):
        self.data = self.data[:-draws]

    def check_data(self):
        if len(self.data) == 0:
            self.load()

    # READING EXTERNAL DATA
    def surf(self, first, limit=0):
        self.next_draw = first
        while self.next_draw:
            self.get_draw_page(self.next_draw)
            if limit and self.visited_pages > limit:
                break

    def get_new_draws(self, year=None) -> list:
        if year and not (2003 < year < current_year):
            year = current_year
        elif not year:
            year = current_year
        url = f"{self.home}archive-resultats-{year}"

        history_page = EuromillionsHistoryPage()
        history_page.get_content(url)
        last_draw_date = self.get_last_draw().date.to_short_french_date_but_whole_month()
        return history_page.get_all_new_archive_links(last_draw_date)

    def get_draw_page(self, draw: str):
        self.current_draw = EuromillionsDraw()
        url = f"{self.result_home}{draw}"
        draw_page = EuroMillionPage()
        draw_page.get_content(url)
        self.set_href(url)

        # Getting balls and stars
        topbox = draw_page.get_topbox_section()
        innerHTML = re.search(r'document\.getElementById\("jsBallOrderCell"\)\.innerHTML = "(.*?)";', topbox.text)
        if innerHTML:
            innerHTML = innerHTML.group(1).replace(r'\"', '"')
            draw_page.set_container(innerHTML)
            balls = draw_page.fetch_items('new ball')
            stars = draw_page.fetch_items('new lucky-star')
        elif topbox.find('div', id='jsBallOrderCell'):
            jsBallOrderCell = topbox.find('div', id='jsBallOrderCell')
            draw_page.set_container(jsBallOrderCell)
            balls = draw_page.fetch_items('new ball')
            stars = draw_page.fetch_items('new lucky-star')
        else:
            raise NotImplemented('#Error: No balls found')
        self.set_balls(balls, stars)

        # Getting prizes
        winners = draw_page.get_first_table()
        foreigns_winners = draw_page.get_foreign_prize_table()
        self.read_table(winners)
        for table in foreigns_winners:
            country = self.get_country(table.get('id'))
            self.read_table(table, country)

        # Getting bets, jackpot, id and date/hour
        found = 0
        for paragraph in draw_page.get_paragraphs():
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

        # Getting nav buttons
        prev_draw, next_draw = draw_page.get_nav_buttons()
        self.set_navigation(prev_draw, next_draw)

        display.print(self.current_draw)
        self.set_draw(self.current_draw)
        self.visited_pages += 1

    def get_country(self, country_id):
        country_id = country_id[-2:]
        if country_id in self.countries:
            country_id = country_id.lower()
        elif country_id == 'GB':
            country_id = 'uk'
        else:
            # wrong country
            raise ValueError(f'Unknown Country: {country_id}')
        return country_id

    def set_href(self, url):
        self.current_draw.href = url

    def set_balls(self, balls, stars):
        self.current_draw.balls = balls
        self.current_draw.stars = stars

    def set_navigation(self, prev, next):
        self.current_draw.prev_draw = prev
        self.current_draw.next_draw = next
        self.next_draw = next

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
                prize.amount_total = clean_number(cells[3] if len(cells) > 4 else '0')
                prize.winners_total = clean_number(cells[4] if len(cells) > 4 else cells[3])
                self.current_draw.prizes[country].append(prize)
                cat += 1
        except IndexError:
            return

    # WRITING DATA
    def update(self):
        if self.is_loaded:
            ldraw: EuromillionsDraw = self.get_last_draw()
            display.print("Last draw date:", ldraw.date.to_date())
            now = self.init_time
            if args.force and now.strftime("%a") in ('mar.', 'ven.'):
                display.print(now.hour, now.minute)
                if now.hour == 21 and now.minute > 15:
                    display.print('let\'s update')
                else:
                    display.print('draw has not been celebrated')
                return

            new_draws = self.get_new_draws()
            if len(new_draws) > 0:
                for new_draw in new_draws:
                    display.print(f"UPDATING FROM: {self.result_home}{new_draw}")
                    self.get_draw_page(new_draw)
                self.save()
            else:
                display.print("No update is needed. No such new draw found.")

    def get_next_draw_day(self):
        date = date_handler(today)
        msg = 'Prochain tirage: '
        if date.get_weekday('int') in (2, 5) and date.get_hour() < 21:
            print(f"{msg}aujourd'hui.")
            return
        date.set_time(hour=21, minute=0)
        while date.get_weekday('int') not in (2, 5):
            date.add_one_day()
        print(f"{msg}{date.to_short_french_datetime_with_weekday()}")


class Statistics(Euromillions):
    def __init__(self):
        Euromillions.__init__(self)
        # Loading data.
        if 'euromillions' in globals():
            self.data = euromillions.data
        else:
            self.load()

        # WARNING: if skip method is used, update self.last_5_draws list.
        self.last_5_draws = self.get_stats_from_draws(5)

    # STATS
    def find_draw(self, targeted_draw, matches=4) -> list:
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

    def find_draw_tuple(self, balls: tuple, matches=4) -> list:
        draws = []
        for draw in self.data:
            hits = 0
            for ball in balls:
                if ball in draw.balls:
                    hits += 1
            if hits >= matches:
                draw.matches = hits
                draws.append(draw)
        return draws

    def get_weight_occurrences(self) -> FrequenceDict:
        self.check_data()
        occ = FrequenceDict()
        for draw in self.walk():
            weight = draw.get_weight()
            occ.add(weight)
        return occ

    def get_ten_first_weights(self) -> list:
        occ = self.get_weight_occurrences()
        return [k for k in occ.keys_sorted_by_values()][:10]

    def get_balls_by_years(self) -> tuple:
        self.check_data()

        balls = dict([(x, FrequenceDict()) for x in range(1, 51)])
        stars = dict([(x, FrequenceDict()) for x in range(1, 13)])

        for draw in self.walk(reverse=True):
            year = draw.get_year()
            for ball in draw.balls:
                balls[ball].add(year)
            for star in draw.stars:
                stars[star].add(year)

        # Some balls never appear.
        years = tuple(y for y in range(self.get_last_draw().date.get_year(), 2003, -1))
        for ball in balls:
            if balls[ball].size() < len(years):
                for year in years:
                    if balls[ball].get(year) is None:
                        balls[ball].reset(year)
        return balls, stars

    def get_stats_from_draws(self, times) -> dict:
        self.check_data()
        i = 1
        draws = []
        balls = FrequenceDict()
        stars = FrequenceDict()
        for draw in reversed(self.data):
            draws.append(
                {
                    'id': draw.id,
                    'date': draw.date.to_short_french_date(),
                    'balls': draw.sorted_balls(),
                    'stars': draw.sorted_stars()
                }
            )
            for ball in draw.balls:
                balls.add(ball)
            for star in draw.stars:
                stars.add(star)
            if len(draws) == times:
                break
        balls.sort()
        stars.sort()
        return {'draws': tuple(draws), 'balls': balls, 'stars': stars}

    def last_seen(self, ball) -> int:
        for draw in self.walk(reverse=True):
            if ball in draw.balls:
                return draw.id

    def seen_in_draws(self, ball: int) -> tuple:
        draws = []
        for draw in self.walk(True):
            if ball in draw.balls:
                draws.append(draw)
        return tuple(draws)

    def generate_ball_frequences(self) -> dict:
        ldraw_id = self.get_last_draw().id
        display.empty_line()
        for ball in range(1, 51):
            appearances = [draw.id for draw in self.seen_in_draws(ball)]
            frequence = [appearances[i] - appearances[i + 1] for i in range(len(appearances[:-1]))]
            length = len(frequence)
            avg = sum(frequence) // length
            last_seen = ldraw_id - appearances[0]
            max_freq = max(frequence)
            last_10_freq = frequence[:-(len(frequence) - 10)]
            yield {
                'ball': ball, 'size': len(appearances), 'lastseen': last_seen,
                'maxfreq': max_freq, 'avg': avg, 'last10freq': last_10_freq,
                'appearances': appearances
            }

    def get_dozens_frequences(self) -> FrequenceDict:
        dozens = FrequenceDict()
        for draw in self.walk(True):
            dozens.add(draw.get_dozens())
        return dozens

    def get_dozens_appearances(self):
        dozens_dict = {}
        for draw in self.walk(True):
            dozens = draw.get_dozens()
            if dozens in dozens_dict:
                dozens_dict[dozens].append(draw.id)
            else:
                dozens_dict[dozens] = [draw.id]
        dozens = self.get_dozens_frequences()
        last_draw_id = self.get_last_draw().id
        ready = []
        preready = []
        postready = []
        for key in dozens.keys(False):
            appearances = dozens_dict[key]
            frequences = [appearances[i] - appearances[i + 1] for i in range(len(appearances[:-1]))]
            seen = last_draw_id - appearances[0]
            if len(frequences):
                avg = sum(frequences) // len(frequences)
                print(key, len(appearances), seen, max(frequences), min(frequences), avg, frequences, appearances)
                if seen == avg:
                    ready.append(key)
                elif seen - 1 == avg:
                    preready.append(key)
                elif seen + 1 == avg:
                    postready.append(key)
            else:
                print(key, len(appearances), seen, frequences, appearances)
        print(f"PREREADY: {preready}\nREADY: {ready}\nPOSTREADY: {postready}")

    def show_dozens_frequences(self):
        dozens = self.get_dozens_frequences()
        for dozen in dozens.keys_sorted_by_values():
            display.print(dozen, dozens[dozen])

    # SHOWING STATS
    def find_all_draw_matches(self, matches=4):
        self.check_data()
        i = 0
        stack = []
        draw_dict1 = FrequenceDict()
        draw_dict2 = FrequenceDict()
        for draw in self.data:
            draws = self.find_draw(draw, matches)
            draw_dict1.set(draw.id, len(draws))
            if len(draws) > 0:
                display.debug(
                    f'DRAW #{draw.id} {draw.date.to_short_french_date()} {draw.balls} has got the following matches:')
                for dr in draws:
                    display.debug(f'\t#{dr.id}', dr.date.to_short_french_date(), dr.balls, dr.matches)
                    stack.append(dr)
                    draw_dict2.add(dr.id)
                i += 1
        display.debug(i)
        display.debug(f"draws with x draws\n[{draw_dict1.size()}]:", draw_dict1.sort_by_values())
        display.debug(f"draws repeated x times\n[{draw_dict2.size()}]: {draw_dict2.sort_by_values()}")
        return stack

    def show_stats_from_draws(self, size=5):
        display.print(f"#{size}")
        items = self.get_stats_from_draws(size)
        draws, balls, stars = items['draws'], items['balls'], items['stars']
        display.print(draws)
        display.print(balls.size(), balls)
        display.print(stars.size(), stars, '\n\n')

    def show_last_5_draws(self):
        display.title('last 5 draws')
        last_5_draws = self.get_stats_from_draws(5)
        for draw in last_5_draws['draws']:
            display.print(draw['id'], draw['date'], draw['balls'], draw['stars'])
        display.print(len(last_5_draws['balls']), last_5_draws['balls'])

    def reduced_forecast(self):
        ten_first_weights = self.get_ten_first_weights()
        all_repeated_draws = self.find_all_draw_matches(4)
        i = 0
        last_draw = self.get_last_draw()

        # reduced version
        reduced_potentials = []
        reduced_matches = FrequenceDict()
        reduced_weights = FrequenceDict()
        for draw in all_repeated_draws:
            weight = draw.get_weight(draw.balls)
            if weight in ten_first_weights:
                seen_balls = set()
                holes = draw.get_holes()
                draw_sum = draw.get_sum()
                for ball in draw.balls:
                    if ball in last_draw.balls:
                        seen_balls.add(ball)
                if seen_balls:
                    i += 1
                    reduced_weights.add(weight)
                    draw.seen_balls = seen_balls
                    for ball in draw.balls:
                        reduced_matches.add(ball)
                    reduced_potentials.append(draw)
                    drawid = f'#{draw.id}'
                    display.print(
                        f'{i:>2}', f'{drawid:>5}', draw.date.to_short_french_date(), draw.balls, draw.stars,
                        weight, draw_sum, holes, len(seen_balls), set(seen_balls)
                    )
        reduced = {
            'potentials': reduced_potentials,
            'matches': reduced_matches,
            'weights': reduced_weights
        }

        # let's print!
        display.empty_line()
        reduced['matches'].sort()
        reduced['weights'].sort()
        display.print(f"matches[{reduced['matches'].size()}]: {reduced['matches']}")
        display.print(f"{'':>12}", reduced['matches'].keys())
        display.print(f"weights[{reduced['weights'].size():> 2}]: {reduced['weights']}")
        display.empty_line()

        return reduced

    def extended_forecast(self):
        last_draw = self.get_last_draw()
        ten_first_weights = self.get_ten_first_weights()

        # extended version
        extended_potentials = []
        extended_matches = FrequenceDict()
        extended_weights = FrequenceDict()
        for draw in self.walk():
            weight = draw.get_weight()
            if draw.get_weight() in ten_first_weights:
                seen_balls = set()
                if 0 < len(draw.get_consecutives_by_length()) < 3:
                    if 0 < len(draw.get_repeated_tens()) < 3:
                        if 0 < len(draw.get_repeated_unities()) < 3:
                            for ball in draw.balls:
                                extended_matches.add(ball)
                                if ball in last_draw.balls:
                                    seen_balls.add(ball)
                            if 0 < len(seen_balls) < 3:
                                draw.seen_balls = seen_balls
                                extended_potentials.append(draw)
                                extended_weights.add(weight)
        i = 1
        for draw in extended_potentials:
            print(
                f"{i} #{draw.id} {draw.date.to_short_french_date()} {draw.sorted_balls()} {draw.seen_balls} {draw.get_weight()} {draw.get_sum()} "
                f"{draw.get_consecutives()} {draw.get_repeated_unities()} {draw.get_repeated_tens()} "
                f"{draw.get_dozens()}"
            )
            i += 1

        self.show_last_5_draws()
        return {
            'potentials': extended_potentials,
            'matches': extended_matches,
            'weights': extended_weights
        }

    def surmise(self, forecast):
        wrinkles = []
        last_draw = self.get_last_draw()
        last_5_draws_seen_balls = self.last_5_draws['balls'].keys()
        display.debug(last_5_draws_seen_balls)

        for draw in forecast['potentials']:
            wrinkle = [min(draw.balls), 0, 0, 0, max(draw.balls)]
            generated = []

            # head, tail and first middle balls
            if min(draw.balls) not in last_draw.balls and max(draw.balls) not in last_draw.balls:
                wrinkle[1] = list(draw.seen_balls)[0]
            else:
                for b in forecast['matches'].keys_sorted_by_values():
                    if b not in wrinkle and wrinkle[0] < b < wrinkle[-1]:
                        wrinkle[1] = b
                        break

            # remaining two balls
            init_wrinkle = list(wrinkle)
            for b in last_5_draws_seen_balls:
                if b > wrinkle[-1] or b + 1 > wrinkle[-1]:
                    break
                if b < wrinkle[0] or b - 1 < wrinkle[0]:
                    continue
                if b - 1 not in last_5_draws_seen_balls and b not in wrinkle:
                    wrinkle[2] = b - 1
                    wrinkle[3] = b
                elif b not in wrinkle and b + 1 not in last_5_draws_seen_balls:
                    wrinkle[2] = b
                    wrinkle[3] = b + 1
                wrinkle = tuple(sorted(wrinkle))
                if wrinkle not in wrinkles:
                    if self.criteria(draw, wrinkle):
                        wrinkles.append(wrinkle)
                        generated.append(wrinkle)
                wrinkle = list(init_wrinkle)
            if generated:
                display.debug(f"draw: {draw.balls} has generated: {generated}")
        display.debug('\n')
        return wrinkles

    def extreme_forecast(self):
        display.title('long forecast')
        combinatory = Combinatory()
        last_draw: EuromillionsDraw = self.get_last_draw()
        ten_first_weights = self.get_ten_first_weights()
        i = j = 0
        win = euromillions.get_last_draw().balls
        hits = FrequenceDict()
        for c in combinatory.short_walk():
            found = []
            hit = []
            draw: EuromillionsDraw = EuromillionsDraw()
            draw.balls = c[1]
            for ball in c[1]:
                if ball in last_draw.balls:
                    found.append(ball)
                if ball in win:
                    hit.append(ball)
            if 2 > len(found) > 0:
                if self.criteria(draw, c[1]) and draw.get_weight() in ten_first_weights:
                    i += 1
                    if len(hit) > 1:
                        j += 1
                        hits.add(len(hit))
                        print(i, j, c, found, f'#{len(hit)}', hit)
        display.print("HITS", hits)
        display.end()

    def criteria(self, draw: EuromillionsDraw, seq: tuple):
        consec = draw.get_consecutives_by_length(seq)
        repunities = draw.get_repeated_unities(seq)
        reptens = draw.get_repeated_tens(seq)
        dozens = draw.get_dozens(seq)

        if consec and 3 not in consec and 4 not in consec:
            if 2 > len(repunities) > 0:
                if 2 > len(reptens) > 0:
                    if '3' not in dozens and '4' not in dozens:
                        if 0 not in seq:
                            return True
        return False

    def show_stats(self):
        display.title('STATS')
        self.show_stats_from_draws(500)
        self.show_stats_from_draws(200)
        self.show_stats_from_draws(100)
        self.show_stats_from_draws(50)
        self.show_stats_from_draws(20)
        self.show_stats_from_draws(10)
        self.show_stats_from_draws(5)
        display.end()

    def quick_forecast(self):
        reduced = self.reduced_forecast()
        extended = self.extended_forecast()
        options = {'reduced': reduced, 'r': reduced, 'extended': extended, 'e': extended}
        choice = options[args.forecast] if 'args' in globals() and args.forecast in options else reduced
        prognoses = self.surmise(choice)

        display.print("\nLet's bet this combinations:")
        i = 1
        freq = FrequenceDict()
        for prognosis in prognoses:
            progn_matches = self.find_draw_tuple(prognosis)
            if sum(draw.matches for draw in progn_matches) == 0:
                display.print(f'\t{i} {prognosis}')
                for b in prognosis:
                    freq.add(b)
                i += 1
        freq.sort()
        display.print(freq.size(), freq)

        if args.target and args.skip > 0:
            draw_id = self.get_last_draw().id + 1
            targeted_draw = euromillions.get_draw(draw_id)
            print(f'\nCOMPARE.\ntarget: {targeted_draw.id} {targeted_draw.balls}')
            hits = []
            for prognosis in prognoses:
                seen = set()
                for ball in prognosis:
                    if ball in targeted_draw.balls:
                        seen.add(ball)
                if len(seen) > 1:
                    hits.append((prognosis, len(seen), seen))
            if hits:
                i = 1
                for hit in hits:
                    print(f'\t{i:>2}.- {hit}')
                    i += 1
            else:
                print('NO LUCK. TRY NEXT WEEK :(')

    def get_friends(self, ball) -> FrequenceDict:
        friends = FrequenceDict()
        for draw in self.walk():
            if ball in draw.balls:
                balls = list(draw.balls)
                balls.remove(ball)
                for b in balls:
                    friends.add(b)
        return friends

    def get_stats(self) -> dict:
        self.data = euromillions.data
        categories = {
            'repunities': FrequenceDict(),
            'reptens': FrequenceDict(),
            'consecutives': FrequenceDict(),
            'weight': FrequenceDict(),
            'dozens': FrequenceDict(),
            'dozen groups': FrequenceDict(),
            'sum': FrequenceDict(),
            'seen': FrequenceDict()
        }

        # calculated statistic categories
        for draw in self.walk():
            categories['weight'].add(draw.get_weight())
            categories['dozens'].add(draw.get_dozens())
            consec = len(draw.get_consecutives_by_length()) #'+'.join([str(x) for x in draw.get_consecutives_by_length()]) #sum(draw.get_consecutives_by_length())
            repunities = len(draw.get_repeated_unities()) #'+'.join(str(len(ru)) for ru in draw.get_repeated_unities()) #sum([len(ru) for ru in draw.get_repeated_unities()])
            reptens = len(draw.get_repeated_tens()) #'+'.join(str(len(ru)) for ru in draw.get_repeated_tens()) #sum([len(rt) for rt in draw.get_repeated_tens()])
            categories['consecutives'].add(consec)
            categories['repunities'].add(repunities)
            categories['reptens'].add(reptens)
            categories['sum'].add(draw.get_sum())

        # dozen groups category
        groups = {}
        for item in categories['dozens'].keys():
            group = draw.get_dozen_group(item)
            groups.update({group: groups.get(group, 0) + categories['dozens'][item]})
        for key in groups:
            categories['dozen groups'].set(key, groups[key])

        #seen category
        for draw in self.walk(True):
            cur_draw_balls = draw.balls
            prev_draw_balls = euromillions.get_draw(draw.id+1).balls if draw.id+1 <= euromillions.length else []
            seen_balls = [b for b in cur_draw_balls if b in prev_draw_balls]
            categories['seen'].add(len(seen_balls))
        if display.debug_bool:
            for cat in categories:
                display.print(cat, categories[cat].sort_by_values())
        return categories

    def show_balls_by_years_table(self):
        balls, stars = self.get_balls_by_years()
        display.print("   " + " ".join(str(y) for y in range(2019, 2003, -1)))
        for ball in balls:
            display.print(f"{ball:>02}", " ".join(f"{balls[ball].get(y):>4}" for y in reversed(balls[ball].keys(True))),
                          f"{sum(balls[ball].values()):>4}")
        for star in stars:
            display.print(f"{star:>02}", " ".join(f"{stars[star].get(y):>4}" for y in reversed(stars[star].keys(True))))

    def show_ball_frequences(self):
        display.title('ball frequences')
        for gen in self.generate_ball_frequences():
            display.print(
                f"{gen['ball']:>2} seen: {gen['size']:>4}, last seen: {gen['lastseen']:>2}, "
                f"max freq: {gen['maxfreq']:>2}, freq avg: {gen['avg']:>2}, last 10 freq: "
                f"{', '.join('%2i' % x for x in gen['last10freq']):>17}, "
                f"apperances: {gen['appearances']}"
            )

    def crosses(self, limit=5):
        display.title('crosses')
        # if limit == 0, there is no limit.
        loop = 1
        for draw in self.walk(True):
            display.print(draw.date.to_short_ISO(), '\t'.join('×' if b in draw.balls else '' for b in range(1, 51)))
            if limit and loop >= limit:
                break
            loop += 1
        display.end()

    def show_weight(self, limit=5):
        display.title('weight')
        # if limit == 0, there is no limit.
        loop = 1
        tab = '\t'
        for draw in self.walk(True):
            print(
                f"{draw.date.to_slashed_french_date()}\t{tab.join(str(b) for b in draw.sorted_balls())}\t"
                f"{draw.get_dozens()}\t{draw.get_weight()}\t"
                f"{tab.join(dr.date.to_slashed_french_date() for dr in self.find_draw(draw))}"
            )
            if limit and loop >= limit:
                break
            loop += 1

    def show_raw_ball_frequence(self):
        display.title('ball freq')
        balls, stars = self.get_balls_by_years()
        tab = '\t'
        for g in self.generate_ball_frequences():
            ball = balls[g['ball']]
            remains = g['avg'] - g['lastseen']
            display.print(
                f"{g['ball']}\t{g['size']}\t{g['lastseen']}\t{g['maxfreq']}\t{g['avg']}\t{remains}\t"
                f"{tab.join(str(f) for f in g['last10freq'])}\t"
                f"{tab.join(str(ball.get(y)) for y in reversed(ball.keys(True)))}\t"
                f"{tab.join(str(a) for a in g['appearances'])}"
            )

    def get_pair_points(self, draw: EuromillionsDraw):
        pairs = stats.pairs()
        selected = ((0, 0), 0)
        for pair in combinations(draw.balls, 2):
            points = pairs.get(pair)
            if points > selected[1]:
                selected = (pair, points)
        return selected[1] / pairs.max()

    def ponderate(self, draw):
        mark = 0
        statistics = self.get_stats()
        display.debug("KEYS", statistics.keys())
        consec = -len(draw.get_consecutives_by_length())
        weight = draw.get_weight()
        mark += consec
        mark += statistics['weight'].size() - statistics['weight'].key_index(weight)
        dozen_group = draw.get_dozen_group()
        mark += (statistics['dozen groups'].size() - statistics['dozen groups'].key_index(dozen_group))
        points = 0
        points += self.get_pair_points(draw)
        print("MARK:", mark, "POINTS:", points)


    def compare(self, targeted_draw, matches=3):
        display.title('compare')
        display.print(f'TARGETED DRAW: {targeted_draw.balls}')
        i = 0
        for draw in self.walk():
            seen = set()
            if draw.id == targeted_draw.id:
                continue
            for ball in draw.balls:
                if ball in targeted_draw.balls:
                    seen.add(ball)
            if seen and len(seen) >= matches:
                i += 1
                print(f"\t{i} {draw.date.to_short_french_date()} {draw.sorted_balls()} {len(seen)} {seen}")

    def pairs(self) -> FrequenceDict:
        i = j = 0
        comb_dict: FrequenceDict = FrequenceDict()
        for comb in combinations(range(1, 51), 2):
            i += 1
            for draw in self.walk():
                if comb[0] in draw.balls and comb[1] in draw.balls:
                    j += 1
                    comb_dict.add(comb)
                    display.debug(f"{j:>5}", draw.date.to_short_french_date(), draw.balls, comb)
                    # comb_dict.update({comb: comb_dict.get(comb, 0) + 1})
        display.debug(i, j, comb)
        display.debug(comb_dict.sort_by_values())
        return comb_dict

    def triplets(self) -> FrequenceDict:
        i = j = 0
        comb_dict = FrequenceDict()
        for comb in combinations(range(1,51), 3):
            i += 1
            for draw in self.walk():
                if comb[0] in draw.balls and comb[1] in draw.balls and comb[2] in draw.balls:
                    j += 1
                    display.debug(f"{j:>5}", draw.date.to_short_french_date(), draw.balls, comb)
                    comb_dict.add(comb)
        display.debug(i, j, comb)
        display.debug(comb_dict.sort_by_values())
        return comb_dict

class Combinatory:
    def __init__(self):
        self.balls = tuple(range(1, 51))
        self.stars = tuple(range(1, 13))
        self.dozens = tuple(range(0, 6))

    def long_walk(self):
        i = 0
        for b in combinations(self.balls, 5):
            for s in combinations(self.stars, 2):
                i += 1
                yield (i, b, s)

    def short_walk(self):
        i = 0
        for c in combinations(self.balls, 5):
            i += 1
            yield (i, c)

    def get_dozens_keys(self):
        return tuple(
            [
                "{0[0]}{0[1]}{0[2]}{0[3]}{0[4]}".format(c)
                for c in product(self.dozens, repeat=5)
                if sum(c) == 5
            ]
        )

    def get_dozen_group(self, dozen: str):
        """
        '12101' -> '@1112'
        '30101' -> '@113'
        """
        rtn = '@'
        rtn += '1' * dozen.count('1')
        rtn += '2' * dozen.count('2')
        rtn += '3' * dozen.count('3')
        rtn += '4' * dozen.count('4')
        rtn += '5' * dozen.count('5')
        return rtn

def test():
    euromillions.load()
    draw = euromillions.data[-7]
    display.print(draw)
    draws = euromillions.find_draw(draw, 4)
    for draw in draws:
        display.print(draw)
    display.print(euromillions.data[-8])
    display.print(f"DATE: {euromillions.data[-1].date.to_date():%Y/%m/%d}")


def test2():
    draw = EuromillionsDraw()
    draw.balls = (2, 3, 34, 12, 29)
    combinatory = Combinatory()
    for dozen in combinatory.get_dozens_keys():
        print (f'{dozen} -> {draw.get_dozen_group(dozen)}')


def fix():
    prev_draw: EuromillionsDraw = None
    i = 0
    for draw in stats.walk(True):
        test_dict = draw.check_data()

        if prev_draw and test_dict['nextdraw'] == -1:
            print(prev_draw.id, prev_draw.date.to_short_french_date())
            draw.next_draw = prev_draw.date.to_short_french_date()
            draw.modified_date = date_handler()

        if test_dict['jackpot'] == -1:
            print('jackpot', draw.jackpot)
            draw_page: EuroMillionPage = EuroMillionPage()
            draw_page.get_content(draw.href)
            print(draw)
            draw_page.get_bets()
            break

        prev_draw = draw
        if i == 4:
            break
        i += 1

    if args.save:
        stats.save()


def mk_stats():
    """
        27/10/19
        consecutives 0 830 65.77
        consecutives 1 405 32.09
        consecutives 2 27 2.14
        consecutives 1+2 432 34.23

        repunities 0 463 36.69
        repunities 1 673 53.33
        repunities 2 126 9.98
        repunities 1+2 799 63.31

        reptens 0 95 7.53
        reptens 1 785 62.2
        reptens 2 382 30.27
        reptens 1+2 1167 92.47

        seen 0 725 57.45
        seen 1 451 35.74
        seen 2 81 6.42
        seen 3 5 0.4
        seen 1+2+3 537 42.55
    """
    percent: Callable[[int, int], Union[float, Any]] = lambda x, y: round((y * 100) / x, 2)
    golden_stats = stats.get_stats()
    for category in ('consecutives', 'repunities', 'reptens', 'seen'):
        accu = 0
        categories = []
        for key in golden_stats[category].keys():
            print(category, key, golden_stats[category][key], percent(euromillions.length, golden_stats[category][key]))
            if key > 0:
                accu += golden_stats[category][key]
                categories.append(key)
        print(category, '+'.join(str(c) for c in categories), accu, percent(euromillions.length, accu))
        print()


if __name__ == '__main__':
    today = datetime.today()
    current_year = today.year
    display = Display()
    date_handler = DateHandler
    from_date = date_handler('2004/02/13').to_short_french_date()
    euromillions = Euromillions()
    euromillions.check_data()
    stats = Statistics()
    intl = Internationalization()
    real_last_draw = euromillions.get_last_draw()

    cmdline = ArgumentParser()
    strue = 'store_true'
    cmdline.add_argument('-b', dest='target', action=strue)
    cmdline.add_argument('-c', dest='compare', action=strue)
    cmdline.add_argument('-D', dest='debug', action=strue)
    cmdline.add_argument('-C', dest='crosses', action=strue)
    cmdline.add_argument('-d', dest='dozens', action=strue)
    cmdline.add_argument(
        '-e',
        dest='forecast',
        action='store',
        choices=('e', 'extended', 'r', 'reduced'),
        default='extended'
    )
    cmdline.add_argument('-F', dest='ballfreq', action=strue)
    cmdline.add_argument('-f', dest='force', action=strue)
    cmdline.add_argument('-G', dest='guess', action=strue)
    cmdline.add_argument('-g', dest='stats', action=strue)
    cmdline.add_argument('-l', dest='last5', action=strue)
    cmdline.add_argument('-m', dest='matches', type=int, default=4)
    cmdline.add_argument('-n', dest='nextdrawday', action=strue)
    cmdline.add_argument('-p', dest='pairs', action=strue)
    cmdline.add_argument('-P', dest='triplets', action=strue)
    cmdline.add_argument('-q', dest='quickforecast', action=strue)
    cmdline.add_argument('-S', dest='showstats', action=strue)
    cmdline.add_argument('-s', dest='skip', type=int)
    cmdline.add_argument('-R', dest='friends', action=strue)
    cmdline.add_argument('-r', dest='showrepdraws', action=strue)
    cmdline.add_argument('-T', dest='test', action=strue, default=False)
    cmdline.add_argument('-t', dest='showtable', action=strue)
    cmdline.add_argument('-u', dest='update', action=strue)
    cmdline.add_argument('-V', dest='save', action=strue)
    cmdline.add_argument('-w', dest='weight', action=strue)
    cmdline.add_argument('-x', dest='x', action=strue)

    args = cmdline.parse_args()
    if args.debug:  # -D
        display.debug_bool = True

    if args.update:  # -u
        euromillions.check_data()
        euromillions.update()

    if args.skip:  # -s \d
        stats.skip(args.skip)
        stats.last_5_draws = stats.get_stats_from_draws(5)

    if args.showstats:  # -S
        stats.show_stats()

    if args.quickforecast:  # -q
        stats.quick_forecast()

    if args.test:  # -T
        # test()
        draw = stats.get_last_draw()
        print(draw.sorted_balls(), draw.get_holes(), draw.get_sum(), draw.get_weight())

    if args.last5:  # -l
        display.empty_line()
        stats.show_last_5_draws()
        display.empty_line()

    if args.showrepdraws:  # -r
        display.debug_bool = True
        stats.find_all_draw_matches(args.matches)
        display.debug_bool = args.debug if args.debug else False

    if args.showtable:  # -t
        display.empty_line()
        stats.show_balls_by_years_table()

    if args.ballfreq:  # -F
        # stats.show_ball_frequences()
        stats.show_raw_ball_frequence()

    if args.compare:  # -c
        draw = stats.get_last_draw()
        stats.compare(draw)

    if args.crosses:  # -C
        stats.crosses()

    if args.weight:  # -w
        stats.show_weight()

    if args.dozens:  # -d
        stats.get_dozens_appearances()

    if args.nextdrawday:  # -n
        stats.get_next_draw_day()

    if args.stats:  # -g
        mk_stats()

    if args.friends:  # -R
        best_dict = {}
        for ball in range(1, 51):
            friends = stats.get_friends(ball)
            print(ball, friends.sort_by_values())
            friends.sort_by_values()
            max = list(friends.keys_sorted_by_values())[0]
            best_dict.setdefault((ball, max), friends.get(max))
        print (best_dict)

    if args.guess:  # -G
        draw = EuromillionsDraw()
        draw.balls = (6, 45, 29, 12, 48)
        draw.stars = (9, 7)

        print(stats.ponderate(draw))

        print(draw.balls, draw.get_dozens(), draw.get_dozen_group())

    if args.pairs:
        pairs = stats.pairs()
        display.print(pairs.sort_by_values())
        pair = (26, 27)
        if pair[1] < pair[0]:
            pair = (pair[1], pair[0])
        print(f"{pair[0]}|{pair[1]}:", pairs.get(pair))

    if args.triplets:
        triplets = stats.triplets()
        display.print(triplets.sort_by_values())

    draw = EuromillionsDraw()
    draw.balls = (23, 27, 34, 36, 48)
    stats.ponderate(draw)
    dozen = draw.get_dozens()
    display.print(dozen, Combinatory().get_dozen_group(dozen))
    # fix()
    """run: -qnSCwrF"""
