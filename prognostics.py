import json
import re
from datetime import datetime
from selae.selaesql import EuroSQL
from selae.statistics import Statistics, combinations, EuromillionsDraw, EuroPrize

class Prognostics:
    def __init__(self):
        self.stats = Statistics()
        self.data = self.stats.data
        self.max = len(self.data)
        self.dozens_blacklist_re = re.compile(r'2[01]*3|3[01]*2|4|5')

    def flashback(self, count=1):
        self.stats.flash_back(count)

    def get_average_of(self, dict_, key, get_avg=False):
        """
        Agafem les dades centrals dels valors d'un diccionari.
        El diccionari és del tipus
            - {'xxyy': {'lastseen': iii, 'delta': nnn, ...}}
            - {zzz: {'lastseen': iii, 'delta': nnn, ...}}
        """
        vk = [(dict_[k][key], k) for k in dict_]
        vk.sort()
        values = [v for v, k in vk]
        keys = [k for v, k in vk]
        z = sum(values) / len(values) if get_avg else 0
        avg = min(values, key=lambda x: abs(z-x))
        i = values.index(avg)
        return {'keys': keys, 'index': i, 'avg': avg, 'dict': dict(zip(keys, values))}

    def fetch_special_number(self):
        """"
        parella | aparicions | freqüència | max | min | delta
        """
        self.stats.header("stars")
        dict_ = {}
        min_last_seen = self.max
        max_last_seen = 0
        max_target_key = ''
        min_target_key = ''

        for sn in combinations(range(1, 13), 2):
            key = f'{sn[0]:02}{sn[1]:02}'
            freq_data = self.stats.specnumb_frequence(key)
            freq_data['lastseen'] = self.max - freq_data['list'][0]
            freq_data['delta'] = freq_data['freq'] - freq_data['lastseen']
            dict_[key] = freq_data
            if freq_data['lastseen'] < min_last_seen:
                min_last_seen = freq_data['lastseen']
                min_target_key = key
            if freq_data['lastseen'] > max_last_seen:
                max_last_seen = freq_data['lastseen']
                max_target_key = key
        delta = self.get_average_of(dict_, 'delta')
        last_seen = self.get_average_of(dict_, 'lastseen', True)
        freq = self.get_average_of(dict_, 'freq', True)

        print("max", max_last_seen, max_target_key)
        print("min", min_last_seen, min_target_key)
        self.show(delta, 'delta')
        self.show(freq, 'freq')
        delta_target = freq['dict'][delta['keys'][delta['index']]]
        print("DELTA TARGET:", delta['keys'][delta['index']], delta_target)

        i=.3
        nearest = self.get_nearest(freq, 'freq', delta_target, i)
        while len(nearest)<3:
            i+=.3
            nearest = self.get_nearest(freq, 'freq', delta_target, i)
        print("nearest:", ', '.join(nearest))


        self.show(last_seen, 'last_seen')


    def fetch_number(self):
        """"
        número | aparicions | freqüència | max | min | delta
        """
        self.stats.header('numbers', first=True)
        dict_ = {}
        min_last_seen = self.max
        max_last_seen = 0
        max_target_key = ''
        min_target_key = ''

        for n in range(1, 51):
            freq_data = self.stats.number_frequence(n)
            freq_data['lastseen'] = self.max - freq_data['list'][0]
            freq_data['delta'] = freq_data['freq'] - freq_data['lastseen']
            dict_[n] = freq_data
            if freq_data['lastseen'] < min_last_seen:
                min_last_seen = freq_data['lastseen']
                min_target_key = n
            if freq_data['lastseen'] > max_last_seen:
                max_last_seen = freq_data['lastseen']
                max_target_key = n
        delta = self.get_average_of(dict_, 'delta')
        last_seen = self.get_average_of(dict_, 'lastseen', True)
        freq = self.get_average_of(dict_, 'freq', True)

        print("max", max_last_seen, max_target_key)
        print("min", min_last_seen, min_target_key)
        self.show(delta, 'delta')
        self.show(freq, 'freq')
        delta_target = freq['dict'][delta['keys'][delta['index']]]
        print("DELTA TARGET:", delta['keys'][delta['index']], delta_target)

        i=.03
        nearest = self.get_nearest(freq, 'freq', delta_target, i)
        while len(nearest)<3:
            i+=.03
            nearest = self.get_nearest(freq, 'freq', delta_target, i)
        print("nearest:", ', '.join(nearest))

        self.show(last_seen, 'last_seen')

    def fetch_dozens(self):
        """"
        parella | aparicions | freqüència | max | min | delta
        """
        self.stats.header('dozens')
        dict_ = {}
        min_last_seen = self.max
        max_last_seen = 0
        max_target_key = ''
        min_target_key = ''
        dgroups = self.stats.dozen_groups()

        for dozen in self.stats.dozen_permutations():
            dgroup = dgroups.get(dozen, [])
            freq_data = self.stats.get_frequence(dgroup)
            freq_data['lastseen'] =  self.max - freq_data['list'][0] if freq_data['list'] else self.max
            freq_data['delta'] = freq_data['freq'] - freq_data['lastseen']
            dict_[dozen] = freq_data
            if freq_data['lastseen'] < min_last_seen:
                min_last_seen = freq_data['lastseen']
                min_target_key = dozen
            if freq_data['lastseen'] > max_last_seen:
                max_last_seen = freq_data['lastseen']
                max_target_key = dozen
        delta = self.get_average_of(dict_, 'delta')
        last_seen = self.get_average_of(dict_, 'lastseen', True)
        freq = self.get_average_of(dict_, 'freq', True)

        print("max", max_last_seen, max_target_key)
        print("min", min_last_seen, min_target_key)
        self.show(delta, 'delta')
        self.show(freq, 'freq')
        delta_target = freq['dict'][delta['keys'][delta['index']]]
        print("DELTA TARGET:", delta['keys'][delta['index']], delta_target)

        i=2
        nearest = self.get_nearest(freq, 'freq', delta_target, i)
        while len(nearest)<3:
            i+=1
            nearest = self.get_nearest(freq, 'freq', delta_target, i)
        print("nearest:", ', '.join(nearest))

        self.show(last_seen, 'last_seen')

    def show(self, dict_, string):
        print(
            f"{string} AVG({dict_['avg']:.3f})",
            dict_['keys'][dict_['index'] - 1],
            dict_['keys'][dict_['index']],
            dict_['keys'][dict_['index'] + 1]
        )

    def get_nearest(self, dict_, string, target=0, range_=1):
        nearest = []
        target = target if not target else dict_['avg']
        for key in dict_['dict']:
            if dict_['dict'][key] - range_ < target < dict_['dict'][key] + range_:
                nearest.append((dict_['dict'][key], key))
        nearest.sort()
        return [str(k) for v, k in nearest]

    def wizard(self):
        i=0
        j=0
        last_id = len(self.data.keys())
        last_draw = self.data[last_id]
        print (last_draw.numbers)
        last_five_draw_balls = []

        #TODO: self.stats.balls_in_last_5() MUST RETURN always the list!
        for i in range(1,5):
            draw = self.data[last_id-i]
            print(draw.numbers)
            for ball in draw.numbers:
                if ball not in last_five_draw_balls and ball not in last_draw.numbers:
                    last_five_draw_balls.append(ball)
        print (len(last_five_draw_balls), last_five_draw_balls)
        candidates = []
        for c in combinations(range(1,51), 5):
            #for s in combinations(range(1,13), 2):
            i += 1
            stats = self.stats
            m1 = [] #Has any ball from last draw
            m2 = [] #Has any ball from last 5 draws
            for n in c:
                if n in last_draw.numbers:
                    m1.append(n)
                elif n in last_five_draw_balls:
                    m2.append(n)
            consec = stats.get_consecutives(c)
            has_hard_consec = self.has_hard_consec(c)
            dozens = stats.get_dozens(c)
            reptens = stats.get_repeated_tens(c)
            repunits = stats.get_repeated_unities(c)
            step = c[-1] - c[0]
            if (
                    #(len(m1) + len(m2) == 1) and # que hi haja un número dels 5 darrers sortejos ## 2092098 122307
                    ((len(m1) == 1 and len(m2) < 3 ) or (0 < len(m2) < 3)) and # que almenys hi haja un número repetit del darrer sorteig i un de 5 darrers ## 2092099 391761
                    #len(consec)== 1 and # que els consecutius no siguen més de 1 grup
                    3 > len(consec) > 0 and # que els consecutius siguen 1 o 2
                    not has_hard_consec and # que els consecutius no siguen més de dos
                    '4' not in dozens and # que no hi haja 4 de la mateixa desena
                    not ('3' in dozens and '2' in dozens) and # que les desenes no tinguen una de 3 i l'altra de 2
                    (50 > step > 21) # que l'amplada siga entre 49 i 22
            ):
                j += 1
                # print (
                #     i, j, c,
                #     "consec:", consec, has_hard_consec,
                #     "dozens:", dozens,
                #     "reptens", reptens,
                #     "repunits", repunits,
                #     "step", step,
                #     "ballsINlastdraw:", m1,
                #     "ballsINlastdraw:", m2
                # )
                result = eurosql.get_match(c, 4)
                if len(result)>0:
                    #print (result)
                    candidates.append(
                        (len(candidates)+1, *c, len(consec), len(reptens), len(repunits), step, len(m1), len(m2), len(result))
                    )
                    if len(candidates)%100==0:
                        print (len(candidates), candidates[-1])
        i=1
        for candidate in candidates:
            print (i, candidate)
            i+=1
        with open('temp.dat', 'w', encoding='utf8') as f:
            json.dump(candidates, f, indent=4)

    def has_hard_consec(self, numbers):
        consec = self.stats.get_consecutives(numbers)
        if len(consec)>1:
            return True
        for t in consec:
            if len(t)>2:
                return True
        return False

    def candidates(self):
        i=1
        for combination in combinations(range(1, 51), 5):
            record = self.evaluate(combination)
            yield (i, record['consec'], record['reptens'], record['repunit'], record['step'], record['ponderate'])
            i += 1

    def evaluate_step(self, step):
        accepted_steps = eurosql.get_table_keys('resum amplades', 'step')[:10]
        if step in accepted_steps:
            return 1
        else:
            return 0

    def evaluate_sequences(self, seq):
        if len(seq) == 2 and len(seq[0]) + len(seq[1]) == 5:
            return 0
        elif len(seq) == 1 and len(seq[0]) > 3:
            return 0
        elif len(seq) == 0:
            return 0
        return 1

    def set_candidates(self):
        cursor = eurosql.cursor()
        cols = "`bola1`, `bola2`, `bola3`, `bola4`, `bola5`, `consec`, `reptens`, `repunit`, `step`, `ponderació`"
        i=1
        for candidate in self.candidates():
            values = "(%s)" % ','.join(str(c) for c in candidate[1:])
            sql = "INSERT INTO candidates(%s) VALUES %s" % (cols, values)
            if i%1000 == 0 or i == 1:
                print (candidate)
            cursor.execute(sql)
            i += 1
        print (candidate)
        eurosql.connection.commit()
        eurosql.close()

    def prognose(self):
        with open('temp.dat', 'r', encoding='utf8') as f:
            data = json.load(f)
        eurosql.set_connection(eurosql.config_dict())
        cols = '(`%s`)' % ('`, `'.join(eurosql.get_column_names('prognostic')))
        print (cols)
        init = 0
        end = len(data)
        splitted = 10000
        cursor = eurosql.cursor()
        for next in range(splitted, len(data), splitted):
            values = ''
            if len(data)-next == len(data)%splitted:
                next = end
            for item in data[init:next]:
                values += '(%s), ' % ', '.join(str(x) for x in item)
            init = next
            values = values.strip(', ')
            print (data[next-1])

            sql = 'INSERT INTO prognostic %s VALUES %s' % (cols, values)
            cursor.execute(sql)
        eurosql.connection.commit()
        eurosql.close()

    def eulgorithm(self, year=None):
        """
        SELECT * FROM boles WHERE EXTRACT(YEAR FROM data_sorteig) = 2019 ORDER BY `id_sorteig` DESC
        :return:
        """
        where = f'EXTRACT(YEAR FROM `data_sorteig`) = {year} ORDER BY `id_sorteig` DESC LIMIT 0, 200'

        where2 = f"""
        GREATEST(`bola1`,`bola2`,`bola3`,`bola4`,`bola5`)-LEAST(`bola1`,`bola2`,`bola3`,`bola4`,`bola5`) IN 
        (SELECT * FROM `deu primeres amplades`) 
	    AND (
	        /* 1 bola */
	        bola1 IN (SELECT * FROM `darrer sorteig`)
	        OR
	        bola2 IN (SELECT * FROM `darrer sorteig`)
	        OR
	        bola3 IN (SELECT * FROM `darrer sorteig`)
	        OR
	        bola4 IN (SELECT * FROM `darrer sorteig`)
	        OR
	        bola5 IN (SELECT * FROM `darrer sorteig`)
	        OR
	        /* 2 boles */
            bola1 IN (SELECT * FROM `darrer sorteig`) AND bola2 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola1 IN (SELECT * FROM `darrer sorteig`) AND bola3 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola1 IN (SELECT * FROM `darrer sorteig`) AND bola4 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola1 IN (SELECT * FROM `darrer sorteig`) AND bola5 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola2 IN (SELECT * FROM `darrer sorteig`) AND bola3 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola2 IN (SELECT * FROM `darrer sorteig`) AND bola4 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola2 IN (SELECT * FROM `darrer sorteig`) AND bola5 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola3 IN (SELECT * FROM `darrer sorteig`) AND bola4 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola3 IN (SELECT * FROM `darrer sorteig`) AND bola5 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola4 IN (SELECT * FROM `darrer sorteig`) AND bola5 IN (SELECT * FROM `darrer sorteig`)
            OR
	        /* 3 boles */
            bola1 IN (SELECT * FROM `darrer sorteig`) AND bola2 IN (SELECT * FROM `darrer sorteig`) AND bola3 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola1 IN (SELECT * FROM `darrer sorteig`) AND bola2 IN (SELECT * FROM `darrer sorteig`) AND bola4 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola1 IN (SELECT * FROM `darrer sorteig`) AND bola2 IN (SELECT * FROM `darrer sorteig`) AND bola5 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola2 IN (SELECT * FROM `darrer sorteig`) AND bola3 IN (SELECT * FROM `darrer sorteig`) AND bola4 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola2 IN (SELECT * FROM `darrer sorteig`) AND bola3 IN (SELECT * FROM `darrer sorteig`) AND bola4 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola2 IN (SELECT * FROM `darrer sorteig`) AND bola4 IN (SELECT * FROM `darrer sorteig`) AND bola5 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola3 IN (SELECT * FROM `darrer sorteig`) AND bola4 IN (SELECT * FROM `darrer sorteig`) AND bola5 IN (SELECT * FROM `darrer sorteig`)
            /* 4 boles */
            OR
            bola1 IN (SELECT * FROM `darrer sorteig`) AND bola2 IN (SELECT * FROM `darrer sorteig`) AND bola3 IN (SELECT * FROM `darrer sorteig`) AND bola4 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola1 IN (SELECT * FROM `darrer sorteig`) AND bola2 IN (SELECT * FROM `darrer sorteig`) AND bola3 IN (SELECT * FROM `darrer sorteig`) AND bola5 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola1 IN (SELECT * FROM `darrer sorteig`) AND bola2 IN (SELECT * FROM `darrer sorteig`) AND bola4 IN (SELECT * FROM `darrer sorteig`) AND bola5 IN (SELECT * FROM `darrer sorteig`)
            OR
            bola2 IN (SELECT * FROM `darrer sorteig`) AND bola3 IN (SELECT * FROM `darrer sorteig`) AND bola4 IN (SELECT * FROM `darrer sorteig`) AND bola5 IN (SELECT * FROM `darrer sorteig`)
        )
	    """
        if year: where2 += f"AND EXTRACT(YEAR FROM data_sorteig) = {year} "
        where2 += "ORDER BY GREATEST(`bola1`,`bola2`,`bola3`,`bola4`,`bola5`)-LEAST(`bola1`,`bola2`,`bola3`,`bola4`,`bola5`) DESC, data_sorteig DESC;"

        eurosql.set_connection(eurosql.config_dict())
        cursor = eurosql.cursor
        candidates = []
        darrer_sorteig = eurosql.lastdraw()[0]
        boles = darrer_sorteig['bola1'], darrer_sorteig['bola2'], darrer_sorteig['bola3'], darrer_sorteig['bola4'], \
                darrer_sorteig['bola5']
        ball_list = list(boles)
        ball_list.sort()
        print (year, ball_list)
        eurosql.truncate_table('`darrer sorteig`')
        eurosql.insert_into('`darrer sorteig`', ('bola',), raw=', '.join('(' + str(b) + ')' for b in  boles))
        eurosql.connection.commit()
        i = 1
        for record in eurosql.match('boles', where2):
            #print (i, *record.values())
            boles = [record['bola1'], record['bola2'], record['bola3'], record['bola4'], record['bola5']]
            boles.sort()
            evaluate = self.evaluate(boles)
            boles.insert(5, record['estrella2'])
            boles.insert(5, record['estrella1'])
            ball_tuple = *boles, *evaluate.values()
            if ball_tuple[-1] == 3:
                print ('\t', i, record['data_sorteig'], ball_tuple)
                i += 1
        eurosql.close()
        print("\n")

    def evaluate(self, seq):
        consec = self.stats.get_consecutives(seq)
        reptens = self.stats.get_repeated_tens(seq)
        repunit = self.stats.get_repeated_unities(seq)
        step = seq[-1] - seq[0]
        dozens = self.stats.get_dozens(seq)
        ponderate = 0
        if not self.dozens_blacklist_re.search(dozens):
            ponderate += self.evaluate_sequences(consec)
        if ponderate > 0:
            ponderate += self.evaluate_sequences(reptens)
            ponderate += self.evaluate_sequences(repunit)
        return {
                   'consec': len(consec),
                   'reptens': len(reptens),
                   'repunit': len(repunit),
                   'step': step,
                   'dozens': dozens,
                    'ponderate': ponderate
        }

    def test(self):
        numbers = (1, 2, 3, 5, 7)
        consec = self.stats.get_consecutives(numbers)
        reptens = self.stats.get_repeated_tens(numbers)
        repunit = self.stats.get_repeated_unities(numbers)
        dozens = self.stats.get_dozens(numbers)
        ponderate = 0
        if not self.dozens_blacklist_re.search(dozens):
            ponderate = self.evaluate_sequences(consec)

        if ponderate > 0:
            self.evaluate_sequences(repunit)
            self.evaluate_sequences(reptens)
        print("CONSEC", len(consec), self.evaluate_sequences(consec))
        print("REPUNIT", len(repunit), self.evaluate_sequences(repunit))
        print("REPTENS", len(reptens), self.evaluate_sequences(reptens), reptens)
        print("DOZENS", len(dozens), dozens, self.dozens_blacklist_re.search(dozens))
        print("PONDER", ponderate)
        print(self.has_hard_consec(numbers))
        print(eurosql.get_table_keys('resum amplades', 'step')[:10])

def main():
    #prognostics.flashback(3)
    prognostics.fetch_number()
    prognostics.fetch_dozens()
    prognostics.fetch_special_number()


if __name__ == '__main__':
    now_1 = datetime.now()
    eurosql = EuroSQL()
    eurosql.init()
    prognostics = Prognostics()
    #main()
    #prognostics.wizard()
    #prognostics.prognose()
    now_2 = datetime.now()
    #prognostics.test()
    #prognostics.set_candidates()
    prognostics.eulgorithm()
    print(f'time 1: {datetime.strftime(now_1, "%H:%M:%S")}')
    print(f"time 2: {datetime.strftime(now_2, '%H:%M:%S')}")
    print(f'time 3: {datetime.strftime(datetime.now(), "%H:%M:%S")}')
