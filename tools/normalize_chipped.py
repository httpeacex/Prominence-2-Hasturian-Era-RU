#!/usr/bin/env python3
"""
Приведение расхождений между частями перевода chipped к одному варианту.

Замена идёт по позиционному соответствию английского и русского слова,
а не поиском подстроки: иначе «простой» из перевода Simple попал бы под
правило для Duh, а согласование по родам («красный/красная») ошибочно
считалось бы расхождением.
"""
import json, re

en = json.load(open('modlang/chipped/en_us.json', encoding='utf-8-sig'))
ru = json.load(open('chipped_ru.json', encoding='utf-8'))

# английское слово -> канонические формы по родам (м, ж, с, мн)
CANON = {
    'Unamused': ('недовольный', 'недовольная', 'недовольное', 'недовольные'),
    'Glad':     ('довольный',   'довольная',   'довольное',   'довольные'),
    'Duh':      ('простой',     'простая',     'простое',     'простые'),
}
# варианты, которые надо вытеснить (в любом роде)
STEMS = {
    'Unamused': ('хмур', 'угрюм'),
    'Glad':     ('радостн',),
    'Duh':      ('глуп', 'туп', 'простецк'),
}
ENDING = {'ый': 0, 'ой': 0, 'ий': 0, 'ая': 1, 'яя': 1, 'ое': 2, 'ее': 2, 'ые': 3, 'ие': 3}

report = {}


def gender_of(word):
    """Определяет род по окончанию уже стоящего в переводе прилагательного."""
    for suf, idx in ENDING.items():
        if word.lower().endswith(suf):
            return idx
    return 0


for key, src in en.items():
    if key not in ru:
        continue
    val = ru[key]

    # ── 1. End Stone -> эндерняк (официальная локализация Minecraft) ──
    if 'End Stone' in str(src):
        new = re.sub(r'\bкамн[ея]\s+Кра[яй]\b', 'эндерняка', val)
        new = re.sub(r'\bкамень\s+Края\b', 'эндерняк', new)
        if new != val:
            report['End Stone'] = report.get('End Stone', 0) + 1
            val = new

    # ── 2. прилагательные-характеры: к варианту большинства ──
    ew, rw = str(src).split(), str(val).split()
    if len(ew) == len(rw):
        changed = False
        for i, e in enumerate(ew):
            if e in CANON:
                stems = STEMS[e]
                if any(rw[i].lower().startswith(s) for s in stems):
                    rw[i] = CANON[e][gender_of(rw[i])]
                    # первое слово названия — с заглавной
                    if i == 0:
                        rw[i] = rw[i][0].upper() + rw[i][1:]
                    report[e] = report.get(e, 0) + 1
                    changed = True
        if changed:
            val = ' '.join(rw)

    ru[key] = val

json.dump(ru, open('chipped_ru.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('Замен выполнено:')
for k, v in sorted(report.items(), key=lambda x: -x[1]):
    print(f'  {v:>4}x  {k}')

print('\nПроверка после нормализации:')
for group in (('эндерняк', 'камень Края'), ('недовольн', 'хмур', 'угрюм'),
              ('довольн', 'радостн'), ('простой', 'глуп', 'туп', 'простецк')):
    counts = {g: sum(1 for v in ru.values() if g.lower() in str(v).lower())
              for g in group}
    print('  ' + ' / '.join(f'{g}: {c}' for g, c in counts.items()))
