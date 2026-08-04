#!/usr/bin/env python3
"""
Скачивание модов сборки и аудит покрытия русским языком.

Из каждого jar берутся только языковые файлы — сам jar после разбора
удаляется, чтобы не держать на диске 885 МБ.
"""
import json, os, sys, zipfile, io, urllib.request, concurrent.futures as cf

IDX = '/agent/workspace/loc/pack/modrinth.index.json'
OUT = '/agent/workspace/loc/modlang'
WORKERS = 12

os.makedirs(OUT, exist_ok=True)
manifest = json.load(open(IDX, encoding='utf-8'))
mods = [f for f in manifest['files'] if f['path'].startswith('mods/')]


def handle(entry):
    name = entry['path'].split('/')[-1]
    url = entry['downloads'][0]
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'PixelForge/1.0'})
        with urllib.request.urlopen(req, timeout=180) as r:
            blob = r.read()
    except Exception as e:
        return {'jar': name, 'error': f'download: {e}'}

    try:
        z = zipfile.ZipFile(io.BytesIO(blob))
    except Exception as e:
        return {'jar': name, 'error': f'zip: {e}'}

    langs = {}
    for n in z.namelist():
        parts = n.split('/')
        # assets/<modid>/lang/<locale>.json
        if (len(parts) == 4 and parts[0] == 'assets'
                and parts[2] == 'lang' and parts[3].endswith('.json')):
            modid, loc = parts[1], parts[3][:-5]
            langs.setdefault(modid, {})[loc] = n

    rec = {'jar': name, 'namespaces': {}}
    for modid, locs in langs.items():
        info = {'has_en': 'en_us' in locs, 'has_ru': 'ru_ru' in locs,
                'locales': sorted(locs)}
        if 'en_us' in locs:
            try:
                d = json.loads(z.read(locs['en_us']).decode('utf-8-sig'))
                info['en_keys'] = len(d)
                info['en_chars'] = sum(len(str(v)) for v in d.values())
                info['adv_keys'] = sum(1 for k in d if k.startswith('advancement'))
                info['block_keys'] = sum(1 for k in d if k.startswith('block.'))
                info['item_keys'] = sum(1 for k in d if k.startswith('item.'))
                # сохраняем en_us для последующего перевода
                p = os.path.join(OUT, modid)
                os.makedirs(p, exist_ok=True)
                open(os.path.join(p, 'en_us.json'), 'wb').write(z.read(locs['en_us']))
            except Exception as e:
                info['en_error'] = str(e)
        if 'ru_ru' in locs:
            try:
                d = json.loads(z.read(locs['ru_ru']).decode('utf-8-sig'))
                info['ru_keys'] = len(d)
                p = os.path.join(OUT, modid)
                os.makedirs(p, exist_ok=True)
                open(os.path.join(p, 'ru_ru.json'), 'wb').write(z.read(locs['ru_ru']))
            except Exception as e:
                info['ru_error'] = str(e)
        rec['namespaces'][modid] = info
    return rec


results = []
done = 0
with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for rec in ex.map(handle, mods):
        results.append(rec)
        done += 1
        if done % 40 == 0:
            print(f'  обработано {done}/{len(mods)}', flush=True)

json.dump(results, open('/agent/workspace/loc/mod_audit.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

errs = [r for r in results if 'error' in r]
print(f'\nГотово. Модов обработано: {len(results)}, ошибок: {len(errs)}')
for e in errs[:10]:
    print('  ', e['jar'], e['error'][:80])
