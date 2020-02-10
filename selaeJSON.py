import json
import pickle
import re
import requests

from selae.selae20 import Euromillions, EuromillionsDraw, EuroPrize
from core import DateHandler


class SelaeAPI:
    """
    19/09/19
    https://www.loteriasyapuestas.es/servicios/buscadorSorteos?game_id=EMIL&fechaInicioInclusiva=20040101&fechaFinInclusiva=20200101&celebrados=true
    https://www.loteriasyapuestas.es/servicios/proximosv3?game_id=EMIL&num=2

    https://www.loteriasyapuestas.es/va/euromillones/estadisticas
    https://www.loteriasyapuestas.es/va/resultados/euromillones
    """

    def __init__(self):
        self.home = 'https://www.loteriasyapuestas.es/servicios/'
        self.data = []
        self.data_filename = 'data/eurojson.bin'

    def buscador(self, game, start_date, end_date, done=True):
        """
        validar start_date i end_date
        start_date han de ser dates vàlides i start_date ha de ser inferior a end_date
        :param game:
        :param start_date:
        :param end_date:
        :param done:
        :return:
        """
        params = f"game_id={game}&fechaInicioInclusiva={start_date}&fechaFinInclusiva={end_date}&celebrados=true"
        getter = requests.get(f"{self.home}buscadorSorteos?{params}")
        json_obj = getter.content
        return json.loads(json_obj)

    def insert(self, items):
        date = items[0]
        balls = items[1]
        stars = items[2]
        if date_handler(self.data[-1][0]).to_date() < date_handler(date).to_date():
            self.data.append((date, balls, stars))

    def surf(self, year=2004, month=6, day=30):
        while year < date_handler().get_year() + 1:
            first_param = f"{year}{month - 5:02}{1:02}"
            second_param = f"{year}{month:02}{day:02}"
            draws = self.buscador('EMIL', first_param, second_param)

            first_draw = draws[-1]
            last_draw = draws[0]
            if isinstance(draws, str):
                print("ERROR:", draws)
                break
            draws.reverse()

            for draw in draws:
                date = date_handler(draw['fecha_sorteo']).to_short_ISO()
                balls = [int(i) for i in re.findall('(\d+)', draw['combinacion'])]
                stars = balls[-2:]
                balls = balls[:-2]
                self.insert((date, balls, stars))

            if month == 6:
                day = 31
                month = 12
            else:
                day = 30
                month = 6
                year += 1

            print(date_handler(first_draw['fecha_sorteo']).to_short_param(), first_draw)
            print(date_handler(last_draw['fecha_sorteo']).to_short_param(), last_draw)

    def walk(self):
        self.load()
        for draw in self.data:
            yield draw

    def save(self):
        if len(self.data) < 1:
            raise MemoryError('No data to save')
        print("FILENAME:", self.data_filename)
        with open(self.data_filename, 'wb') as f:
            pickle.dump(self.data, f, pickle.HIGHEST_PROTOCOL)
        return True

    def load(self):
        if len(self.data) == 0:
            with open(self.data_filename, 'rb') as f:
                self.data = pickle.load(f)
            return True
        return False

    def estadistiques(self):
        url = 'https://www.loteriasyapuestas.es/va/euromillones/estadisticas'

    def run(self):
        euromillions = Euromillions()
        eurodraws = [draw for draw in euromillions.walk()]
        i = 0
        for draw in self.walk():
            print(draw, eurodraws[i].balls,
                  tuple(sorted(draw[1])) == eurodraws[i].sorted_balls() and 'true' or '---- FALSE ----')
            i += 1


class CompareData:
    def __init__(self):
        self.local_data = SelaeAPI()
        self.local_data.load()

    def get_last_draw(self):
        return self.local_data.data[-1]

    def get_last_draw_date(self):
        return self.get_last_draw()[0]

    def get_delay(self):
        self.diff = date_handler().to_date() - date_handler(self.get_last_draw_date()).to_date()

    def set_month(self):
        date = date_handler(self.get_last_draw_date())
        return 6 if date.get_month() > 6 else 12

    def dispatch(self):
        if self.diff.days > 4:
            month = self.set_month()
            print (month)
            date = date_handler(self.get_last_draw_date())
            selae.surf(date.get_year(), month)
            selae.save()


if __name__ == '__main__':
    date_handler = DateHandler

    selae = SelaeAPI()
    compare = CompareData()
    compare.dispatch()
    selae.run()

