import os
from utils import *
from queue import Queue

config = get_config()
os.chdir(config['path'])

def proc(fn):
    if fn.endswith('.mp3') or fn.endswith('.flac'):
        fn = fn[:fn.rfind('.')]
        song_id = SongSearcher.get_first_result(fn)
        print(song_id)
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
                proc(i)
            else:
                q.put(pd)