#!/usr/bin/env python3
"""
Генерация памяти перевода: карта «английская строка → русский перевод».

Файл не хранится в репозитории, потому что полностью выводится из
data/quests_en.json и data/quests_ru.json — держать третью копию тех же
данных значит рисковать их расхождением.

Использование:
    python3 tools/make_memory.py > translation_memory.json
"""
import json, sys, os

BASE = os.path.join(os.path.dirname(__file__), '..', 'data')

en = json.load(open(os.path.join(BASE, 'quests_en.json'), encoding='utf-8'))
ru = json.load(open(os.path.join(BASE, 'quests_ru.json'), encoding='utf-8'))

memory = {en[k]['en']: ru[k] for k in en if k in ru}

json.dump(memory, sys.stdout, ensure_ascii=False, indent=1)
print(f'\nПар в памяти перевода: {len(memory)}', file=sys.stderr)
