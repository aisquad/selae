import json
import psycopg2

from argparse import ArgumentParser
from itertools import combinations

from selae20 import EuromillionsDraw, EuroPrize, Euromillions, FrequenceDict, Statistics, Combinatory
from core import Display, digital_root
from sql_classes import RecordSet, Select


class SQL:
    def __init__(self):
        self.conn: psycopg2.connect = None
        self.cursor: psycopg2.extensions.cursor = None

    def _get_config(self):
        with open('resources/selae20.json', 'r') as fp:
            params = json.load(fp)
        return params

    def connect(self):
        params = self._get_config()
        self.conn = psycopg2.connect(**params['postgresql'])
        self.cursor = self.conn.cursor()

    def execute(self, command):
        self.cursor.execute(command)

    def get_data(self, command, *args, **kwargs):
        self.execute(command)
        recordset = RecordSet()
        recordset.result = self.cursor.fetchall()
        recordset.headers = tuple(i[0].lower() for i in self.cursor.description)
        return recordset

    def select(self, fields='*', table='', where='', group_by='', order_by=''):
        if where:
            where = f" WHERE {where}"
        if group_by:
            group_by = f" GROUP BY {group_by}"
        if order_by:
            order_by = f" ORDER BY {order_by}"
        self.execute(f"SELECT {fields} FROM {table}{where}{group_by}{order_by};")

    def insert(self, table, fields, values, returning='', commit=True):
        if returning:
            returning = f" RETURNING {returning}"
        self.execute(f"INSERT INTO {table} ({fields}) VALUES ({values}){returning};")
        if commit:
            self.commit()
        return self.cursor.fetchone()

    def update(self, table, field, where, commit=True):
        query = self.get_draws_query(limit=0)
        self.cursor.execute(query)
        update = f"UPDATE {table} SET {field} WHERE {where};"
        self.execute(update)
        if commit:
            self.commit()

    def get_draws_query(self, limit=50, offset=0):
        select = Select()
        balls = ', '.join("ball%i" % i for i in range(1,6))
        fields = ("draws.id, annual_id, date, annual_id", balls, 'star1, star2')
        select.add_fields(fields)
        select.set_table('draws')
        select.add_join('combinations', 'combinations.draw_id = draws.comd_id')
        select.add_order_by('draws.id')
        select.set_limit(limit, offset)
        return select.patch()

    def get_last_draw_query(self):
        return "SELECT * FROM draws ORDER BY id DESC LIMIT 1;"

    def insert_combination(self, draw: EuromillionsDraw):
        fields = "{}, star1, star2".format(', '.join('ball%i' % i for i in range(1,6)))
        values = "{}, {}".format(', '.join(str(b) for b in draw.balls), ', '.join(str(s) for s in draw.stars))
        return self.insert('combinations', fields, values, 'id')

    def insert_draw(self, comb_id, draw: EuromillionsDraw):
        values = {
            'date': draw.date.to_short_ISO(),
            'comb_id': comb_id,
            'a_id': draw.annual_id
        }
        self.insert('draws', 'date, comb_id, annual_id', "CAST('{date}' as DATE), {comb_id}, {ann_id}".format(**values))

    def walk(self, insert_headers=False):
        query = self.get_draws_query(limit=0)
        self.execute(query)
        if insert_headers:
            headers = tuple(i[0].lower() for i in self.cursor.description)
            for draw in self.cursor.fetchall():
                yield dict(zip(headers, draw))
        else:
            for draw in self.cursor.fetchall():
                yield draw

    def update_balls(self):
        for row in self.walk(insert_headers=True):
            for order, ball in enumerate((row['ball1'], row['ball2'], row['ball3'], row['ball4'], row['ball5']), 1):
                self.update('balls', f'"order" = {order}', f"draw_id = {row['id']} AND ball = {ball}")
        self.commit()

    def insert_stars(self):
        for draw in self.walk():
            print(draw)
            for order, star in enumerate((draw['star1'], draw['star2']), 1):
                self.insert("stars", "draw_id, star, appearance_order", f"{draw['id']}, {star}, {order}")

    def find_ball(self, ball=1):
        balls = ', '.join('ball%i' %i for i in range(1, 6))
        fields = f'draw_id, {balls}, star1, star2'
        self.select(fields, 'combinations', f'{ball} IN ({balls})', order_by='draw_id')
        recordset = RecordSet()
        recordset.result = self.cursor.fetchall()
        return recordset

    def find_friends(self, ball=1):
        freq = FrequenceDict()
        # counter = Counter()
        recordset = self.find_ball(ball)
        recordset.as_dict()
        for row in recordset.result:
            balls = [row[key] for key in row.keys() if key.startswith('ball')]
            friends = balls.copy()
            friends.remove(ball)
            stars = [row[key] for key in row.keys() if key.startswith('star')]
            balls.sort()
            stars.sort()
            freq.add_all(friends)
            # counter.update(friends)
            print(row['draw_id'], tuple(balls), tuple(stars))
        freq.sort()
        print(freq)
        # print(dict(counter.most_common()))

    def _find_sets(self, ball1, ball2=0, ball3=0, elem='balls'):
        condition3 = f" AND {ball3} in (ball1, ball2, ball3, ball4, ball5)" if ball3 else ''
        condition2 = ''
        if elem == 'balls' and ball2:
            condition1 = f"{ball1} in (ball1, ball2, ball3, ball4, ball5) AND "
            condition2 = f"{ball2} in (ball1, ball2, ball3, ball4, ball5)"
        elif elem == 'balls' and ball1:
            condition1 = f"{ball1} in (ball1, ball2, ball3, ball4, ball5)"
        elif not ball2:
            condition1 = f"{ball1} in (star1, star2)"
        else:
            condition1 = f"{ball1} in (star1, star2) AND {ball2} IN (star1, star2)"
        query = f"SELECT COUNT(*) FROM combinations WHERE {condition1}{condition2}{condition3};"
        self.execute(query)
        return self.cursor.fetchone()[0]

    def _find_tuple(self, length, elem='balls'):
        limit = 51 if elem == 'balls' else 13
        comb_dict = FrequenceDict()
        for comb in combinations(range(1, limit), length):
            times = self._find_sets(*comb, elem=elem)
            comb_dict.set(comb, times)
        comb_dict.sort()
        print(comb_dict)

    def find_frequences_by_element(self, elem='ball'):
        rtn = dict()
        query = f"SELECT {elem}, COUNT(*) as counter FROM {elem}s GROUP BY {elem} ORDER BY counter DESC;"
        recordset = RecordSet()
        self.execute(query)
        headers = tuple(i[0].lower() for i in self.cursor.description)
        for draw in self.cursor.fetchall():
            d = dict(zip(headers, draw))
            rtn.update({d[elem]: d['counter']})
        return rtn

    def find_frequences_quickly(self):
        balls = self.find_frequences_by_element()
        stars = self.find_frequences_by_element('star')
        return balls, stars

    def find_frequences(self):
        balls = FrequenceDict()
        for ball in range(1, 51):
            times = self._find_sets(ball)
            balls.set(ball, times)
        stars = FrequenceDict()
        for star in range(1, 13):
            times = self._find_sets(star, elem='stars')
            stars.set(star, times)
        balls.sort()
        stars.sort()
        print(balls)
        print(stars)

    def find_duets(self):
        self._find_tuple(2)

    def find_triplets(self):
        self._find_tuple(3)

    def find(self, draws):
        for draw in draws:
            balls = draw[0]
            stars = draw[1]
            where = ''
            balls = ' OR '.join(f"{ball} in (ball1, ball2, ball3, ball4, ball5)" for ball in draw[0])
            stars = ' OR '.join(f"{star} in (star1, star2)" for star in draw[1])

            self.search("SELECT * FROM draws WHERE {balls} OR {stars};")

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()


class EuroMillions(Euromillions):
    def __init__(self):
        Euromillions.__init__(self)

    def run(self):
        self.load()


class Stats(Statistics):
    def __init__(self):
        Statistics.__init__(self)

    def run(self):
        print(self.triplets()['dict'])


def cmdline():
    arg_parser = ArgumentParser()
    arg_parser.add_argument('-H', dest='holes_stats', action='store_true')
    arg_parser.add_argument('-p', '--progn', dest='prognose', action='store_true')
    args = arg_parser.parse_args()


if __name__ == '__main__':
    display = Display()
    stats = Stats()
    sql = SQL()
    sql.connect()

    sql.find(
        ((1, 7, 10, 34, 36), (3, 7)),
        ((3, 6, 9, 30, 32), (3, 7)),
        ((5, 19, 20, 40, 47), (1, 11)),
        ((5, 19, 25, 31, 44), (3, 4))
    )

    sql.close()
