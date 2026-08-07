#!/usr/bin/env python3
"""
Обязательная проверка перед выпуском релиза.

Каждый класс ошибок здесь однажды уже уехал в игру. Проверка сравнивает
перевод с оригинальными языковыми файлами модов построчно и падает, если
найдено хоть одно расхождение в том, что игра трактует как разметку.

    python3 verify.py <архив.zip> <каталог с en_us модов>

Что проверяется и почему:

  битый JSON        файл не загрузится, весь мод останется английским

  битый %           Minecraft разбирает строку перед подстановкой аргументов.
                    Одиночный % вне спецификатора бросает исключение прямо
                    при отрисовке. В процентах писать %%

  спецификаторы     число и тип %s/%d обязаны совпадать с оригиналом.
                    %d вместо %s при строковом аргументе роняет игру

  висячий §         § перед символом, который не является кодом цвета,
                    съедает следующий символ

  потерян глиф      диапазоны E000-FAFF отданы под иконки кастомного шрифта
                    сборки. Визуально похожий обычный символ (U+6012 вместо
                    U+F960) выглядит в редакторе так же, а в игре ломается.
                    Глифы копируются побайтово

  конфликт ключей   Minecraft склеивает языковые файлы всех модов в одну
                    карту. Один ключ с разными значениями в разных
                    пространствах имён даёт недетерминированный результат

  достижения        каждый translate-ключ датапака обязан существовать
                    в языковом файле, иначе игрок увидит сырой ключ
"""
import collections
import hashlib
import io
import json
import os
import re
import sys
import zipfile

FORMAT = re.compile(r'%(?:(\d+)\$)?([A-Za-z%]|$)')
SPEC = re.compile(r'%%|%(\d+)\$([sd])|%([sd])')
DANGLING = re.compile(r'§(?![0-9a-fk-orA-FK-OR])')
SERVICE = ('_comment', '#')


def flat(value):
    """Текст значения. owo-lib разрешает в языковых файлах компоненты."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ''.join(flat(x) for x in value)
    if isinstance(value, dict):
        return str(value.get('text', ''))
    return ''


def breaks_format(text):
    """Повторяет разбор TranslatableContents: остался ли % вне спецификатора."""
    i = 0
    for m in FORMAT.finditer(text):
        if m.start() < i:
            continue
        if m.start() > i and '%' in text[i:m.start()]:
            return True
        i = m.end()
    return '%' in text[i:]


def specifiers(text):
    return sorted(m.group(2) or m.group(3) for m in SPEC.finditer(text)
                  if m.group(0) != '%%')


def glyphs(text):
    return collections.Counter(c for c in text if 0xE000 <= ord(c) <= 0xFAFF)


def load(path):
    try:
        with open(path, encoding='utf-8-sig') as f:
            return json.load(f)
    except Exception:
        return None


def check(archive, sources):
    z = zipfile.ZipFile(archive)
    langs = [n for n in z.namelist() if n.endswith('/lang/ru_ru.json')]
    problems = collections.defaultdict(list)
    seen = collections.defaultdict(set)
    keys = 0

    for name in langs:
        ns = name.split('/assets/')[-1].split('/')[0]
        try:
            ru = json.loads(z.read(name).decode('utf-8-sig'))
        except Exception as exc:
            problems['битый JSON'].append(f'{ns}: {exc}')
            continue
        en = load(os.path.join(sources, ns, 'en_us.json')) or {}
        keys += len(ru)

        for key, value in ru.items():
            got = flat(value)
            src = flat(en[key]) if key in en else None
            if isinstance(value, str) and not key.startswith(SERVICE):
                seen[key].add(value)

            # оригинал мода тоже бывает кривой — это не наша регрессия
            if '%' in got and breaks_format(got) and not (src and breaks_format(src)):
                problems['битый %'].append(f'{ns} / {key}')
            if src is not None and specifiers(got) != specifiers(src):
                problems['спецификаторы'].append(
                    f'{ns} / {key}: было {specifiers(src)}, стало {specifiers(got)}')
            if DANGLING.search(got) and not (src and DANGLING.search(src)):
                problems['висячий §'].append(f'{ns} / {key}')
            if src is not None:
                lost = glyphs(src) - glyphs(got)
                if lost:
                    problems['потерян глиф'].append(
                        f'{ns} / {key}: ' + ' '.join(f'U+{ord(c):04X}' for c in lost.elements()))

    for key, values in seen.items():
        if len(values) > 1:
            problems['конфликт ключей'].append(f'{key}: {sorted(values)}')

    # датапак достижений
    known = set()
    for name in langs:
        try:
            known |= set(json.loads(z.read(name).decode('utf-8-sig')).keys())
        except Exception:
            pass
    for name in [n for n in z.namelist() if n.endswith('.zip')]:
        inner = zipfile.ZipFile(io.BytesIO(z.read(name)))
        for entry in inner.namelist():
            if not (entry.endswith('.json') and '/advancement' in entry):
                continue
            display = json.loads(inner.read(entry).decode('utf-8-sig')).get('display', {})
            for field in ('title', 'description'):
                node = display.get(field)
                if isinstance(node, dict) and node.get('translate') not in known \
                        and 'translate' in node:
                    problems['достижения'].append(f'{entry}: {node["translate"]}')

    raw = open(archive, 'rb').read()
    print(f'{os.path.basename(archive)} — {len(raw)} байт')
    print(f'sha256 {hashlib.sha256(raw).hexdigest()}')
    print(f'языковых файлов {len(langs)}, ключей {keys}\n')

    for kind in ('битый JSON', 'битый %', 'спецификаторы', 'висячий §',
                 'потерян глиф', 'конфликт ключей', 'достижения'):
        found = problems[kind]
        print(('  OK  ' if not found else '  СБОЙ') + f'  {kind}: {len(found)}')
        for line in found[:15]:
            print(f'          {line}')

    return not any(problems.values())


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(0 if check(sys.argv[1], sys.argv[2]) else 1)
