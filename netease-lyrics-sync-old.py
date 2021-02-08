import os
import base64
from queue import Queue
import json
import requests
from mutagen.flac import FLAC
from mutagen.id3 import ID3

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
}
gojuoon =  r'あアいイうウえエおオかカきキくクけケこコさサしシすスせセそソたタちチつツてテとトなナにニぬヌねネのノはハひヒふフへヘほホまマみミむムめメもモやヤゆユよヨらラりリるルれレろロわワをヲんン'

def sreq(url, timeout):
    for i in range(10):
        try:
            response = requests.get(url, headers = headers, timeout = timeout)
            return response
        except:
            pass
    return '{}'

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

'''------------------------lyrics fetcher start------------------------'''
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
        return 'lrc' in self.raw.keys() and self.raw['lrc']['lyric'] != None
    
    def get_original_lyrics(self):
        return self.raw['lrc']['lyric']
    
    def have_translation(self):
        return len(self.raw['tlyric']['lyric']) > 0
    
    def get_translated_lyrics(self):
        return self.raw['tlyric']['lyric']
'''------------------------lyrics fetcher end------------------------'''

'''------------------------song searcher start------------------------'''
class SongSearcher:
    base_url = r'http://music.163.com/api/search/get/web?csrf_token=hlpretag=&hlposttag=&s={}&type=1&offset=0&total=true&limit=20'

    @staticmethod
    def get_first_result(name):
        url = SongSearcher.base_url.format(name)
        res = ''
        try:
            res = json.loads(sreq(url, 2000).content)
            res = res['result']['songs']
            return res[0]['id']
        except:
            print('error: ')
            print(res)
        return 0
    
    @staticmethod
    def get_best_match(title, album, artist):
        url = SongSearcher.base_url.format(title)
        res = ''
        # print('title', title, 'album', album, 'artist', artist)
        try:
            res = json.loads(sreq(url, 2000).content)
            res = res['result']['songs']
        except:
            print('error:')
            print(res)
            return 0
        
        best_score = 0
        best_id = 0

        for i in res:
            score = 0
            if i['name'] == title:
                # print('title same')
                score += 5
            elif i['name'] in title or title in i['name']:
                score += 4
            if i['artists'][0]['name'] == artist:
                # print('artists same')
                score += 3
            elif i['artists'][0]['name'] in artist or artist in i['artists'][0]['name']:
                score += 2
            if i['album']['name'] == album:
                # print('album same')
                score += 2
            elif i['album']['name'] in album or album in i['album']['name']:
                score += 1
            
            if score > best_score:
                best_score = score
                best_id = i['id']
            
        print(best_score)
        return best_id
'''------------------------song searcher end------------------------'''

def proc(fn):
    if fn.endswith('.mp3'):
        p = ID3(fn)
        title = p['TIT2'].text[0]
        album = p['TALB'].text[0]
        artist = p['TPE1'].text[0]
    else:
        p = FLAC(fn)
        title = p['title'][0]
        album = p['album'][0]
        artist = p['artist'][0]
    
    fn = fn[:fn.rfind('.')]
    song_id = SongSearcher.get_best_match(title, album, artist)
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
            elif config['japanese'] == 'sync':
                data = [[i[:10], i[10:]] for i in orig.split('\n') + trans.split('\n') if len(i) > 10 and i[0] == '[']
                data.sort(key = lambda x: x[0])
                data = '\n'.join([i[0] + i[1] for i in data])
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
                print('now at ' + i)
                if i.endswith('.mp3') or i.endswith('.flac'):
                    proc(i)
            else:
                q.put(pd)