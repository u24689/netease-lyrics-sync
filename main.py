import os
from utils import *

config = get_config()
os.chdir(config['path'])

for i in os.listdir():
    if i.endswith('.mp3') or i.endswith('.flac'):
        i = i[:i.rfind('.')]
        song_id = SongSearcher.get_first_result(i)
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
            
            if config['simplify']:
                data = simplify(data)
            
            with open(i + '.lrc', 'w+', encoding = 'utf-8') as f:
                f.write(data)