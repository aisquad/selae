from core import SQL
from selae.selae19 import Euromilions, EuromilionsDraw
from configparser import ConfigParser
from datetime import datetime
from itertools import combinations

class EuroSQL(SQL):
    def __init__(self):
        SQL.__init__(self)
        self.euromilions = Euromilions()

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
        for draw_id, draw in self.euromilions.data.items():
            if draw_id in keys:
                continue
            # print (draw_id, draw.numbers, draw.special_numbers)
            values = list(draw.numbers)
            values.append(draw.special_numbers[0])
            values.append(draw.special_numbers[1])
            values.append(f'{datetime.now():%Y-%m-%d %H:%M:%S}')
            # values.insert(0, draw_id)
            values.insert(0, f"{draw.datetime:%Y-%m-%d}")
            self.insert_into(table, cols, values)
            self.connection.commit()

    def init(self):
        self.set_connection(self.config_dict())
        self.euromilions.load()

    def get_match(self, numbers, r):
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

    def got_matches(self):
        draws = self.euromilions.data
        i=0
        draw_set = set()
        for draw in draws:
            numbers = draws[draw].numbers
            match = self.get_match(numbers, 4)
            if len(match) > 1:
                i+=1
                print (
                    f"{i: >3}.- {draws[draw].datetime:%Y/%m/%d} {draws[draw].numbers} [{len(match)-1}] -> ",
                    [
                        (
                            f"{mdraw['data_sorteig']:%Y/%m/%d}",
                            mdraw['bola1'],
                            mdraw['bola2'],
                            mdraw['bola3'],
                            mdraw['bola4'],
                            mdraw['bola5'],
                        )
                            for mdraw in match if mdraw['data_sorteig'] if f"{draws[draw].datetime:%Y/%m/%d}" != f"{mdraw['data_sorteig']:%Y/%m/%d}"
                    ]
                )
                draw_set.add(draw)
        print ("TOTAL:", len(draw_set), list(sorted(draw_set)))

    def run(self):
        try:
            self.update()
            self.got_matches()
        finally:
            self.connection.close()


if __name__ == "__main__":
    eurosql = EuroSQL()
    eurosql.init()
    eurosql.run()
