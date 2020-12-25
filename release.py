import os
from queue import Queue
import json
import requests


headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
}
gojuoon =  r'あアいイうウえエおオかカきキくクけケこコさサしシすスせセそソたタちチつツてテとトなナにニぬヌねネのノはハひヒふフへヘほホまマみミむムめメもモやヤゆユよヨらラりリるルれレろロわワをヲんン'

def sreq(url, timeout):
    for i in range(100):
        try:
            response = requests.get(url, headers = headers, timeout = timeout)
            return response
        except:
            pass
    raise Exception('timeout for 100 times')

def simplify(s):
    res = ''
    for j in s.split('\n'):
        if len(j) >= 11 and j[0] == '[' and j[10] == ']':
            res += j[:9]
            res += j[10:]
            res += '\n'
        else:
            res += j
            res += '\n'
    return res

def get_config():
    with open('config.txt', 'r+', encoding = 'utf-8') as f:
        lst = list(f.read().split('\n'))
    res = {}
    res['english'] = lst[0].replace('english:', '')
    res['japanese'] = lst[1].replace('japanese:', '')
    res['simplify'] = lst[2].replace('simplify:', '')
    res['path'] = lst[3].replace('path:', '')
    res['scan-subdir'] = lst[4].replace('scan-subdir:', '')
    return res

def is_japanese(s):
    for i in gojuoon:
        if i in s:
            return True
    return False

class LyricsFetcher:
    base_url = r'https://music.163.com/api/song/lyric?id={}&lv=1&kv=1&tv=-1'

    def __init__(self, song_id):
        if not type(song_id) in (str, int):
            raise Exception('song_id should either be a integer or a string')
        elif type(song_id) == int:
            song_id = str(song_id)
        self.song_id = song_id
        self.raw = json.loads(sreq(self.base_url.format(self.song_id), 1000).content.decode())
    
    def have_lyrics(self):
        return 'lrc' in self.raw.keys()
    
    def get_original_lyrics(self):
        return self.raw['lrc']['lyric']
    
    def have_translation(self):
        return len(self.raw['tlyric']['lyric']) > 0
    
    def get_translated_lyrics(self):
        return self.raw['tlyric']['lyric']

class SongSearcher:
    base_url = r'http://music.163.com/api/search/get/web?csrf_token=hlpretag=&hlposttag=&s={}&type=1&offset=0&total=true&limit=20'

    @staticmethod
    def get_first_result(name):
        url = SongSearcher.base_url.format(name)
        res = json.loads(sreq(url, 2000).content)['result']['songs']
        if len(res) == 0:
            return 0
        return res[0]['id']

def proc(fn):
    if fn.endswith('.mp3') or fn.endswith('.flac'):
        fn = fn[:fn.rfind('.')]
        song_id = SongSearcher.get_first_result(fn)
        if song_id == 0:
            return
        lf = LyricsFetcher(song_id)

        if lf.have_lyrics():
            orig = lf.get_original_lyrics()
            trans = lf.get_translated_lyrics()
            data = ''

            if is_japanese(orig):
                if config['japanese'] == 'translation' and lf.have_translation():
                    data = trans
                elif config['japanese'] == 'original':
                    data = orig
            else:
                if config['english'] == 'translation' and lf.have_translation():
                    data = trans
                elif config['english'] == 'original':
                    data = orig
            
            if config['simplify'] == 'true':
                data = simplify(data)
            
            with open(fn + '.lrc', 'w+', encoding = 'utf-8') as f:
                f.write(data)

config = get_config()
os.chdir(config['path'])

if config['scan-subdir'] == 'false':
    for i in os.listdir():
        proc(i)
else:
    q = Queue()
    q.put(config['path'])
    while not q.empty():
        p = q.get()
        print('now at ' + p)
        os.chdir(p)
        for i in os.listdir():
            pd = p + '\\' + i
            if os.path.isfile(i):
                proc(i)
            else:
                q.put(pd)