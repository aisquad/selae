from selae.statistics import Statistics, combinations, EuromilionsDraw

class Prognostics:
    def __init__(self):
        self.stats = Statistics()
        self.data = self.stats.data
        self.max = len(self.data)

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


if __name__ == '__main__':
    prognostics = Prognostics()
    prognostics.fetch_number()
    prognostics.fetch_dozens()
    prognostics.fetch_special_number()
