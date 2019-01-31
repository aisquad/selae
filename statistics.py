from itertools import product, combinations
from argparse import ArgumentParser
from selae.selae19 import Euromilions, EuromilionsDraw, TinyStats

class Number:
    def __init__(self):
        self.number = 0
        self.last_draw_id = 0
        self.last_draw_datetime = None
        self.last_seen = 0
        self.frequence = 0.0
        self.max = 0
        self.all_appearances = 0
        self.last_5 = 0
        self.last_10 = 0
        self.last_20 = 0
        self.last_50 = 0
        self.last_100 = 0
        self.last_200 = 0
        self.last_500 = 0
        self.draw_list = []


class Ball(Number):
    def __init__(self):
        Number.__init__(self)


class Statistics(TinyStats):
    def __init__(self):
        TinyStats.__init__(self)
        euromilions = Euromilions()
        euromilions.load()
        self.data = euromilions.data
        self.balls = {}
        self.save = euromilions.save
        self.skip = 0

    def flash_back(self, count=1):
         self.skip = count

    def get_keys(self):
        if not self.skip:
            for key in reversed(sorted(self.data.keys())):
                yield key
        else:
            next = 0
            for key in reversed(sorted(self.data.keys())):
                if next < self.skip:
                    next += 1
                    continue
                #print(f"#KEY: {key}")
                yield key

    def run(self):
        """
        Obtenim les estadístiques dels 50 números
        """
        for i in range(1, 51):
            ball = Ball()
            ball.number = i
            ball.all_appearances = self.count(i)
            last_seen = self.last_seen(i)
            ball.last_draw_id = last_seen['draw_id']
            ball.last_draw_datetime = last_seen['date']
            ball.last_seen = last_seen['draws']
            freq = self.number_frequence(i)
            ball.frequence = freq['freq']
            ball.max = freq['max']
            ball.draw_list = freq['list']
            ball.last_5 = self.count(i, 5)
            ball.last_10 = self.count(i, 10)
            ball.last_20 = self.count(i, 20)
            ball.last_50 = self.count(i, 50)
            ball.last_100 = self.count(i, 100)
            ball.last_200 = self.count(i, 200)
            ball.last_500 = self.count(i, 500)
            self.balls[i] = ball

    def count(self, number, limit=0):
        """
        Contem el nombre de vegades que ha eixit un número durant els x sortejos.
        """
        counter = 0
        loop = 1
        for key in self.get_keys():
            if number in self.data[key].numbers:
                counter += 1
            if limit and loop > limit - 1:
                break
            loop += 1
        return counter

    def last_seen(self, number):
        """
        Obtenim l'última vegada que s'ha vist un número.
        """
        i = 0
        for key in self.get_keys():
            draw = self.data[key]
            if number in draw.numbers:
                return {'draws': i, 'date': draw.datetime, 'draw_id': key}
            i += 1

    def get_frequence(self, item_list):
        """
        Obtenim la freqüència de les aparicions d'un element.
        Es passa una llista que conté l'id dels sortejos on ha eixit l'element.
        """
        rslt = {"freq": 0.0, "max": 0, "min": 0, 'list': []}
        frequences = []
        for i in range(len(item_list) - 1):
            frequences.append(item_list[i] - item_list[i + 1])

        if frequences:
            rslt["freq"] = sum(frequences) / len(frequences)
            rslt['max'] = max(frequences)
            rslt["min"] = min(frequences)
            rslt['list'] = item_list
        return rslt

    def number_frequence(self, number):
        last_seen_list = []
        for key in self.get_keys():
            draw = self.data[key]
            if number in draw.numbers:
                last_seen_list.append(key)
        return self.get_frequence(last_seen_list)

    def specnumb_frequence(self, stars):
        last_seen_list = []
        for key in self.get_keys():
            special_numbers = sorted(self.data[key].special_numbers)
            if stars == f"{special_numbers[0]:02}{special_numbers[1]:02}":
                last_seen_list.append(key)
        return self.get_frequence(last_seen_list)

    def dozen_groups(self):
        """
        Obtenim un diccionari de les desenes que han aparegut.
        Es registra cada sorteig on apareix.
        Es semblant al que es fa a self.number_frequence(), però
        aplicat a les desenes.
        """
        dozens_dict = {}
        for draw_id in self.get_keys():
            dozens = self.data[draw_id].dozens
            if dozens_dict.get(dozens):
                dozens_dict[dozens].append(draw_id)
            else:
                dozens_dict.update({dozens: [draw_id]})
        return dozens_dict

    def __sum_last_draws(self, property):
        last_draws = []
        for i in self.balls:
            last_draws.append(getattr(self.balls[i], property))
        return sum(last_draws)

    def balls_in_last_5(self):
        ball_list = []
        for i in self.balls:
            if self.balls[i].last_5 > 0:
                ball_list.append(i)
        return ball_list

    def balls_not_in_last_5(self):
        ball_list = []
        for i in self.balls:
            if self.balls[i].last_5 == 0:
                ball_list.append(i)
        return ball_list

    def check_issues(self):
        for i in range(1, 51):
            print(f"{i: >5} {self.balls[i].all_appearances: >7} {self.balls[i].last_5: >5} "
                  f"{self.balls[i].last_10: >5} {self.balls[i].last_20: >5} {self.balls[i].last_50: >5} "
                  f"{self.balls[i].last_100: >5} {self.balls[i].last_200: >5} {self.balls[i].last_500: >5}")
        print(
            f"{len(self.data): >5} {self.__sum_last_draws('all_appearances'): >7} {self.__sum_last_draws('last_5'): >5} "
            f"{self.__sum_last_draws('last_10'): >5} {self.__sum_last_draws('last_20'): >5} "
            f"{self.__sum_last_draws('last_50'): >5} {self.__sum_last_draws('last_100'): >5} "
            f"{self.__sum_last_draws('last_200'): >5} {self.__sum_last_draws('last_500'): >5}"
        )

    def to_cvs(self):
        """
        bola | aparicions | freqüència | max | delta | sortejos des darrera ap |
            darrers 5 | d 10 | d 20 | d 50 |  d 100 | d 200 | d 500 | llista id sortejos
        """
        self.header("NUMBERS", True)
        for i in range(1, 51):
            draws = "\t".join("%i" % d for d in self.balls[i].draw_list)
            diff = self.balls[i].frequence - self.balls[i].last_seen
            print(
                f"{i}\t{self.balls[i].all_appearances}\t{self.balls[i].frequence:.3f}\t"
                f"{self.balls[i].max}\t{diff:.3f}\t{self.balls[i].last_seen}\t{self.balls[i].last_5}\t"
                f"{self.balls[i].last_10}\t{self.balls[i].last_20}\t{self.balls[i].last_50}\t{self.balls[i].last_100}\t"
                f"{self.balls[i].last_200}\t{self.balls[i].last_500}\t{draws}".replace('.', ',')
            )
        #self.csv_summary()

    def csv_summary(self):
        print(
            f"\n{len(self.data)}\t{self.__sum_last_draws('all_appearances')}\t{self.__sum_last_draws('frequence')/50:.3f}"
            f"\t\t\t{self.__sum_last_draws('last_5')}\t{self.__sum_last_draws('last_10')}\t{self.__sum_last_draws('last_20')}\t"
            f"{self.__sum_last_draws('last_50')}\t{self.__sum_last_draws('last_100')}\t"
            f"{self.__sum_last_draws('last_200')}\t{self.__sum_last_draws('last_500')}"
        )


    def to_cvs_short_fmt(self):
        for i in range(1, 51):
            draws = "\t".join("%i" % d for d in self.balls[i].draw_list)
            print(f"{i}\t{self.balls[i].all_appearances}\t{self.balls[i].last_seen}\t"
                  f"{self.balls[i].frequence:.3f}\t{self.balls[i].max}\t{draws}".replace('.', ','))

    def dozen_permutations(self):
        for permutation in product([0, 1, 2, 3, 4, 5], repeat=5):
            if sum(permutation) == 5:
                yield "".join(str(i) for i in permutation)

    def _get_consecutives(self, draw_id):
        draw: EuromilionsDraw = self.data[draw_id]
        numbers = sorted(draw.numbers)
        return self.get_consecutives(numbers)

    def _get_repeated_unities(self, draw):
        numbers = sorted(self.data[draw].numbers)
        return self.get_repeated_unities(numbers)

    def _get_repeated_tens(self, draw):
        numbers = sorted(self.data[draw].numbers)
        return self.get_repeated_tens(numbers)

    def _get_dozens(self, draw):
        numbers = sorted(self.data[draw].numbers)
        return self.get_dozens(numbers)

    def last_draw(self):
        print(self.data[len(self.data)])

    def show_last_draws(self, limit=5):
        i = 1
        for draw_id in self.get_keys():
            if i > limit:
                break
            draw = self.data[draw_id]
            print(draw)
            i += 1

        last_5 = self.balls_in_last_5()
        more = [b for b in range(1,51) if b not in last_5] #self.balls_not_in_last_5()
        print(f"\n\n{len(last_5)}: {last_5}\n{len(more)}: {more}".replace(", ", "\t"))
        print (f"bab: {self.show_balls_by_appearance_order(last_5)}".replace(", ", "\t"))

    def show_balls_by_appearance_order(self, expected_balls=[]):
        """
        Obtenim dos diccionaris que ens indiquen les boles que han eixit en els darrers
        cinc sortejos.
        S'ordenen per ordre d'aparició, els de més a l'esquerra són els més antics. El
        diccionari els tria per desenes.
        """
        by_appearance_order_balls = []
        draw_id = len(self.data)-self.skip
        while len(by_appearance_order_balls)<50:
            draw = self.data[draw_id]
            for ball in draw.numbers:
                if ball in by_appearance_order_balls:
                    by_appearance_order_balls.remove(ball)
                by_appearance_order_balls.insert(0, ball)
            draw_id -= 1
        last_5_dict = {4:[],3:[],2:[],1:[],0:[]}
        remainder_dict = {4:[],3:[],2:[],1:[],0:[]}
        for k in by_appearance_order_balls:
            if k in expected_balls:
                last_5_dict[self.get_dozen(k)].append(k)
            else:
                remainder_dict[self.get_dozen(k)].append(k)
        return {'last 5': last_5_dict, 'remainder balls': remainder_dict}

    def ball_friends(self, number):
        """
        Extraem les boles amb les que eix més la bola que li passem.
        """
        friends = {}
        for draw_id in self.get_keys():
            if number in self.data[draw_id].numbers:
                numbers = list(self.data[draw_id].numbers)
                numbers.remove(number)
                for n in numbers:
                    if friends.get(n):
                        friends[n] += 1
                    else:
                        friends[n] = 1
        return friends

    def dozens_tables(self):
        """
        grup | aparicions | freqüència | max | min | delta | sortejos des darrera ap | llista id sortejos
        """

        self.header("DOZENS")
        dozens_groups = self.dozen_groups()

        for c in self.dozen_permutations():
            d = dozens_groups.get(c, [])
            last_seen = len(self.data) - d[0] if d else len(self.data)
            f = self.get_frequence(d)
            freq = f"{f['freq']:.3f}\t{f['max']}\t{f['min']}"
            strd = '\t'.join([str(s) for s in d])
            delta = f['freq'] - last_seen
            print(f"{c}\t{len(d)}\t{freq}\t{delta:.3f}\t{last_seen}\t{strd}".replace('.', ','))

    def header(self, title: str, first=False):
        head = ""
        if not first:
            head += "\n\n"
        print (f"{head}## -- {title.upper()} -- ##\n")

    def special_number_table(self):
        """"
        parella | aparicions | freqüència | max | min | delta
        """
        sdict = {}
        for sn in combinations(range(1,13), 2):
            key = f'{sn[0]:02}{sn[1]:02}'
            sdict[key] = self.specnumb_frequence(key)

        self.header('STARS')
        for key in sorted(sdict):
            sn = sdict[key]
            last_seen = len(self.data) - sn['list'][0]
            freq = f"{sn['freq']:.3f}\t{sn['max']}\t{sn['min']}"
            draws = '\t'.join(str(s) for s in sn['list'])
            delta = sn['freq'] - last_seen
            print(f"{key}\t{len(sn['list'])}\t{freq}\t{delta:.3f}\t{last_seen}\t{draws}".replace('.', ','))

        self.show_last_draws()

        self.header("BALL FRIENDS")
        for i in range(1, 51):
            friends = self.ball_friends(i)
            print(f"{i}:")
            inv_friends = {}
            for k, v in friends.items():
                inv_friends.setdefault(v, []).append(k)
            best_friends = list(reversed(sorted(inv_friends.keys())))[:5]
            for k in reversed(sorted(inv_friends.keys())):
                if k in best_friends:
                    print("\t", k, tuple(sorted(inv_friends[k])))

    def crosses(self, draw_id=0):
        """
        Mostra les creus per a la fulla de càlcul.
        """
        if not draw_id:
            draw_id = len(self.data)
        cross = '×'
        rtn = "\n\n== # ×+× CROSSES ×+× # ==\n%s\t%s\n" % (' ' * 10, '\t'.join(str(i) for i in range(1,51)))
        draw = self.data[draw_id]
        rtn += f'{draw.datetime:%Y/%m/%d}\t'
        for i in range(1, 51):
            if i in draw.numbers:
                rtn += f'{cross}'
            rtn += '\t'
        rtn += '\n'
        print (rtn)

if __name__ == '__main__':
    stats = Statistics()
    arg_parser = ArgumentParser()
    arg_parser.add_argument('-C', dest='csv', action='store_true')
    arg_parser.add_argument('-c', dest='checkissues', action='store_true')
    arg_parser.add_argument('-k', dest='combinatories', action='store_true')
    arg_parser.add_argument('-R', '--crosses', dest='crosses', action='store', type=int)
    arg_parser.add_argument('-d', dest='dozenstables', action='store_true')
    arg_parser.add_argument('-f', dest='flashback', action='store', type=int)
    arg_parser.add_argument('-r', dest='run', action='store_true')
    arg_parser.add_argument('-s', dest='spectrum', action='store_true')
    arg_parser.add_argument('-t', dest='specnumtable', action='store_true')
    arg_parser.add_argument('-w', dest='watch', action='store_true')
    args = arg_parser.parse_args()

    if args.checkissues:
        stats.check_issues()
    elif args.flashback:
        stats.flash_back(args.flashback)
    if args.run:
        stats.run()
    if args.csv:
        stats.to_cvs()
    if args.dozenstables:
        stats.dozens_tables()
    if args.specnumtable:
        stats.special_number_table()
    if args.crosses is 0 or args.crosses:
        stats.crosses()
