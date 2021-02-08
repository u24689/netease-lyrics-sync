import os
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.filedialog import askdirectory
import pickle
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
appdata_path = os.getenv('APPDATA')

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
    res['y'] = lst[4].replace('y:', '')
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
        return 'lrc' in self.raw.keys() and self.raw['lrc']['lyric'] != None
    
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
        url = SongSearcher.base_url.format(title + ' ' + artist)
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
            
        return best_id

class Config:
    def __init__(self):
        self.data = {}
        self.data['japanese'] = '原文'
        self.data['other'] = '原文'
        self.data['simplify'] = False
        self.data['subdir'] = False
        self.data['path'] = 'C:'
    
    def load_config(self):
        try:
            self.data = pickle.load(open(appdata_path + r'\netease-lyrics-sync\data.pkl', 'rb'))
            return True
        except:
            return False
    
    def save_config(self):
        if not os.path.isdir(appdata_path + r'\netease-lyrics-sync'):
            os.mkdir(appdata_path + r'\netease-lyrics-sync')
        pickle.dump(self.data, open(appdata_path + r'\netease-lyrics-sync\data.pkl', 'wb'))

def proc(fn, config):
    try:
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
    except:
        try:
            a = title
        except:
            title = fn[:fn.rfind('.')]
        try:
            a = album
        except:
            album = ''
        try:
            a = artist
        except:
            artist = ''
    
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
            if config['japanese'] == '翻译' and lf.have_translation():
                data = trans
            elif config['japanese'] == '原文':
                data = orig
            elif config['japanese'] == '对照':
                data = [[i[:10], i[10:]] for i in orig.split('\n') + trans.split('\n') if len(i) > 10 and i[0] == '[']
                data.sort(key = lambda x: x[0])
                data = '\n'.join([i[0] + i[1] for i in data])
        else:
            if config['other'] == '翻译' and lf.have_translation():
                data = trans
            elif config['other'] == '原文':
                data = orig
            elif config['other'] == '对照':
                data = [[i[:10], i[10:]] for i in orig.split('\n') + trans.split('\n') if len(i) > 10 and i[0] == '[']
                data.sort(key = lambda x: x[0])
                data = '\n'.join([i[0] + i[1] for i in data])
            
        if config['simplify'] == True:
            data = simplify(data)
            
        with open(fn + '.lrc', 'w+', encoding = 'utf-8') as f:
            f.write(data)

class MainUI:
    def __init__(self):
        self.build_window()
        self.value_japanese = tk.StringVar(value = '原文')
        self.value_other = tk.StringVar(value = '原文')
        self.value_simplify = tk.BooleanVar(value = False)
        self.value_subdir = tk.BooleanVar(value = False)
        self.value_path = tk.StringVar(value = 'C:')

        self.config = Config()
        if self.config.load_config():
            self.value_japanese.set(self.config.data['japanese'])
            self.value_other.set(self.config.data['other'])
            self.value_simplify.set(self.config.data['simplify'])
            self.value_subdir.set(self.config.data['subdir'])
            self.value_path.set(self.config.data['path'])

        self.value_japanese.trace('w', self.update_config)
        self.value_other.trace('w', self.update_config)
        self.value_simplify.trace('w', self.update_config)
        self.value_subdir.trace('w', self.update_config)
        self.value_path.trace('w', self.update_config)

        self.build()
    
    def build_window(self):
        window = tk.Tk()
        window.title('网易云歌词同步')
        window.configure(background = '#ffffff')
        window.geometry('600x200')
        window.resizable(height = False, width = False)
        self.window = window
    
    def build(self):
        p = ttk.Style()
        p.configure('.', background = '#ffffff')
        
        self.label_frame_japanese = tk.LabelFrame(self.window, text = '日语歌词显示方式', background = '#ffffff')
        self.label_frame_japanese.place(relx = 0.025, rely = 0.05, relheight = 0.3, relwidth = 0.6)
        self.combobox_japanese = ttk.Combobox(self.label_frame_japanese, values = ['原文', '翻译', '对照'], textvariable = self.value_japanese)
        self.combobox_japanese.place(relx = 0.1, rely = 0.15, relheight = 0.6, relwidth = 0.8)

        self.label_frame_other = tk.LabelFrame(self.window, text = '非日语歌词显示方式', background = '#ffffff')
        self.label_frame_other.place(relx = 0.025, rely = 0.4, relheight = 0.3, relwidth = 0.6)
        self.combobox_other = ttk.Combobox(self.label_frame_other, values = ['原文', '翻译', '对照'], textvariable = self.value_other)
        self.combobox_other.place(relx = 0.1, rely = 0.15, relheight = 0.6, relwidth = 0.8)

        self.checkbutton_simplify = ttk.Checkbutton(self.window, text = '将歌词时间变为两位小数，修复NW-A55的歌词识别问题', var = self.value_simplify)
        self.checkbutton_simplify.place(relx = 0.025, rely = 0.75)

        self.checkbutton_subdir = ttk.Checkbutton(self.window, text = '扫描子文件夹', var = self.value_subdir)
        self.checkbutton_subdir.place(relx = 0.025, rely = 0.85)

        self.combobox_path = tk.LabelFrame(self.window, text = '目标路径', background = '#ffffff')
        self.combobox_path.place(relx = 0.65, rely = 0.05, relheight = 0.65, relwidth = 0.3)
        self.text_path = tk.Entry(self.combobox_path, textvariable = self.value_path)
        self.text_path.place(relx = 0.05, rely = 0.05, relwidth = 0.9, relheight = 0.3)
        self.button_path = ttk.Button(self.combobox_path, text = '选择路径', command = self.select_path)
        self.button_path.place(relx = 0.05, rely = 0.5, relwidth = 0.9, relheight = 0.4)

        self.button_start = ttk.Button(self.window, text = '开始', command = self.start)
        self.button_start.place(relx = 0.65, rely = 0.75, relwidth = 0.3, relheight = 0.2)

        self.window.mainloop()
    
    def select_path(self):
        self.value_path.set(askdirectory())
        self.update_config()
    
    def update_config(self, *args):
        self.config.data['japanese'] = self.value_japanese.get()
        self.config.data['other'] = self.value_other.get()
        self.config.data['simplify'] = self.value_simplify.get()
        self.config.data['subdir'] = self.value_subdir.get()
        self.config.data['path'] = self.value_path.get()
        self.config.save_config()

    def start(self):
        self.window.title('网易云歌词同步 处理中')
        config = self.config.data
        os.chdir(config['path'])
        
        if config['subdir'] == False:
            for i in os.listdir():
                proc(i, config)
        else:
            q = Queue()
            q.put(config['path'])
            while not q.empty():
                p = q.get()
                os.chdir(p)
                for i in os.listdir():
                    pd = p + '\\' + i
                    if os.path.isfile(i):
                        if i.endswith('.mp3') or i.endswith('.flac'):
                            proc(i, config)
                    else:
                        q.put(pd)
        self.window.title('网易云歌词同步')

mainUI = MainUI()