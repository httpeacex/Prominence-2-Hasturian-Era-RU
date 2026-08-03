#!/usr/bin/env python3
"""
Нормализация перевода квестбука после слияния частей.

1. Возвращает испанские строки в исходный вид. В квестбуке есть параллельные
   англо-испанские вкладки; переводить надо только английскую, иначе вкладка
   с меткой Español окажется с русским текстом.
2. Приводит расхождения терминов к варианту большинства.
"""
import json, re

en = json.load(open('quests_en.json', encoding='utf-8'))
ru = json.load(open('quests_ru.json', encoding='utf-8'))
es_keys = set(json.load(open('es_keys.json', encoding='utf-8')))

report = {'es_reverted': 0, 'terms': {}}

# ── 1. испанские строки возвращаем как были ──────────────────────────
for k in es_keys:
    if ru.get(k) != en[k]['en']:
        ru[k] = en[k]['en']
        report['es_reverted'] += 1

# ── 2. унификация терминов ───────────────────────────────────────────
# порядок важен: длинные формы раньше коротких
TERMS = [
    # Aberration: в названиях предметов было «Аберрации», в тексте «Выродки».
    # Приводим всё к «Аберрация» — иначе игрок не свяжет моба с его дропом.
    ('Истребление Выродков', 'Истребление Аберраций'),
    ('Убейте Отклонения',    'Убейте аберраций'),
    ('Выродки',              'Аберрации'),
    ('выродков',             'аберраций'),
    ('выродки',              'аберрации'),
    ('выродка',              'аберрации'),
    ('Выродок',              'Аберрация'),
    # Null — босс. Большинство: «Нулл».
    ('Нуль',  'Нулл'),
    # Hex — организация архимагов. Большинство: «Гекс».
    ('Хекса', 'Гекса'),
    ('Хекс',  'Гекс'),
]

for k, v in list(ru.items()):
    if k in es_keys:
        continue
    orig = v
    for a, b in TERMS:
        if a in v:
            v = v.replace(a, b)
            report['terms'][a] = report['terms'].get(a, 0) + 1
    if v != orig:
        ru[k] = v

json.dump(ru, open('quests_ru.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print(f"Испанских строк возвращено в исходный вид: {report['es_reverted']}")
print("Замен терминов:")
for a, c in sorted(report['terms'].items(), key=lambda x: -x[1]):
    print(f"  {c:>3}x  {a}")

# ── контроль: конфликты должны исчезнуть ─────────────────────────────
print("\nПовторная проверка конфликтов:")
for a, b in [('Нулл', 'Нуль'), ('Гекс', 'Хекс'), ('Аберра', 'выродк')]:
    ca = sum(1 for x in ru.values() if a in x)
    cb = sum(1 for x in ru.values() if b in x)
    flag = 'КОНФЛИКТ' if (ca and cb) else 'ok'
    print(f"  {flag}: \"{a}\"={ca}  \"{b}\"={cb}")
