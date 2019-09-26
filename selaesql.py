from argparse import ArgumentParser
from core import SQL, Display
from selae.selae20 import Euromillions, EuromillionsDraw, EuroPrize
from configparser import ConfigParser
from datetime import datetime
from itertools import combinations

class EuroSQL(SQL):
    def __init__(self):
        SQL.__init__(self)
        self.euromillions = Euromillions()

    def config_dict(self):
        cfg = ConfigParser()
        cfg.read('sql.ini')
        conn = cfg['Connection']
        return dict([(k,v) for k,v in conn.items()])

    def get_keys(self):
        keys = self.get_table_keys(table='boles', key_name='id_sorteig')
        return keys

    def update(self):
        """
        Actualitza la base de dates agafant les dades del fitxer euromillones.bin
        """
        table = 'boles'
        cols = ('data_sorteig', 'bola1', 'bola2', 'bola3', 'bola4', 'bola5', 'estrella1', 'estrella2', 'data_insercio')
        keys = self.get_keys()
        for draw in self.euromillions.data:
            if draw.id in keys:
                continue
            display.verbose("INSERT INTO:", draw.id, draw.balls, draw.stars, level=0)
            values = list(draw.balls)
            values.append(draw.stars[0])
            values.append(draw.stars[1])
            values.append(f'{datetime.now():%Y-%m-%d %H:%M:%S}')
            values.insert(0, f"{draw.date.to_date():%Y-%m-%d}")
            self.insert_into(table, cols, values)
            self.connection.commit()

    def lastdraw(self):
        return self.get_last_recordset('boles', 'data_sorteig DESC')

    def init(self):
        self.set_connection(self.config_dict())
        self.euromillions.load()

    def get_match(self, numbers, r=5):
        """
        min: 2, max: len(numbers)

        Obtenim els sortejos que continguen x boles iguals, ha de ser un nombre
        entre 2 i 5.
        """
        if r < 2:
            r = 2
        numbers = tuple(sorted(numbers))
        where = ''
        for combination in combinations(numbers, r):
            for number in combination:
                where += f"{number} IN (bola1, bola2, bola3, bola4, bola5) AND "
            where = where.strip("AND ")
            where += ' OR '
        where = where.strip("OR ")
        return self.match('boles', where)

    def soupify(self, soup):
        i=1
        string = ""
        for key in soup:
            string += f"{i}.- [:{key}:] ->\n\t[#{len(soup[key])}: {', '.join(str(x) for x in soup[key])}#]\n"
            i += 1
        return string

    def got_matches(self, r=4):
        draws = self.euromillions.data
        i=0
        replier_draw = []
        replied_draw = []
        repeated_draws = []
        draw_dict = {}
        for draw in draws:
            numbers = draw.balls
            match =  [md for md in self.get_match(numbers, r) if f"{draw.date.to_date():%Y/%m/%d}" > f"{md['data_sorteig']:%Y/%m/%d}"]
            if len(match) > 0:
                i += 1
                display.print(
                    f"{i: >3}.- [{draw.id: >4}] {draw.date.to_date():%Y/%m/%d} {draw.balls} [{len(match)}] -> ",
                    [
                        (
                            f"[{mdraw['id_sorteig']}] {mdraw['data_sorteig']:%Y/%m/%d}",
                            mdraw['bola1'],
                            mdraw['bola2'],
                            mdraw['bola3'],
                            mdraw['bola4'],
                            mdraw['bola5'],
                        )
                            for mdraw in match
                    ]
                )
                replier_draw.append(draw.id)
                for mdraw in match:
                    if mdraw['id_sorteig'] not in replied_draw:
                        replied_draw.append(mdraw['id_sorteig'])
                    else:
                        repeated_draws.append(mdraw['id_sorteig'])
                    if draw_dict.get(draw):
                        draw_dict[draw.id].append(mdraw['id_sorteig'])
                    else:
                        draw_dict[draw.id] = [mdraw['id_sorteig']]

        display.print ("REPLICATED:", len(replied_draw), replied_draw)
        display.print ("REPLICANT:", len(replier_draw), replier_draw)
        display.print ("REPEATED:", len(repeated_draws), repeated_draws)
        display.print ("REPEATSET:", len(set(repeated_draws)), list(sorted(set(repeated_draws))))
        display.print (self.soupify(draw_dict))

    def run(self):
        try:
            self.update()
            self.got_matches(args.same)
            if args.same > 4:
                self.got_matches(4)
        finally:
            self.connection.close()


if __name__ == "__main__":
    arg_parser = ArgumentParser()
    arg_parser.add_argument('-s', '--same', dest='same', action='store', type=int, default=4)
    args = arg_parser.parse_args()

    display = Display()

    eurosql = EuroSQL()
    eurosql.init()
    eurosql.run()
