#!/usr/bin/env python3
"""
Сборка оверлея русской локализации Prominence II: Hasturian Era v3.9.27.

Собирает четыре поверхности:
  1. config/ftbquests/quests/**.snbt   — уже переведены отдельным шагом
  2. config/puffish_skills/**.json     — замена фраз, глифы и §-коды не трогаются
  3. config/fancymenu/assets/tips.txt  — подсказки загрузки
  4. config/fancymenu/customization/*.txt — метки меню
  5. resourcepack/                     — ru_ru.json мода prominent
"""
import json, os, re, shutil, glob

SRC = 'pack/overrides'
OUT = 'out'

# ══ подсказки загрузочного экрана ═══════════════════════════════════
TIPS = [
    "Раса игрока называется Пламенорождённые. Это третья раса, созданная С'келлаком, наряду с Гномами и Серконидами.",
    "Хастур — единственное Первородное существо Нечистого, что делает его одним из могущественнейших созданий вселенной. Сильнее лишь четыре Вечных Существа.",
    "Вечных Существ четверо — воплощения Созидания, Жизни, Смерти и Разрушения.",
    "С'келлак — Вечное Существо Созидания, воплощение этой Вечной Силы и одна из четырёх сильнейших сущностей мира.",
    "Говорят, что похожий на портал объект в Крае — это не «что-то», а «кто-то».",
    "Ни Добра, ни Зла не существует. Есть лишь противоположные силы, отталкивающие друг друга.",
    "В сборке десятки скрытых квестов-пасхалок под названием «Вечные Испытания». Сможете пройти их все?",
    "«Протуберанец» — событие, пробудившее все Вечные Силы и создавшее Вечных Существ.",
    "Я потратил больше 2000 часов на разработку и тестирование этой сборки и её модов с особым контентом! :) — ElocinDev",
    "Уклонение *(клавиша R)* даёт полсекунды неуязвимости. Успеете поймать момент сильной атаки босса — переживёте её!",
    "Технические моды в Prominence полностью необязательны, но дают массу преимуществ и позволяют автоматизировать почти всё!",
    "В официальной вики Prominence больше 6 часов чтения и подробных руководств!",
    "В Prominence чары вроде Остроты и Небесной кары не исключают друг друга. То же с Защитой, Огнеупорностью, Взрывоустойчивостью и прочими.",
    "Готовьтесь перед боем с боссом: приготовьте еду, сварите зелья, чай или пиво и позаботьтесь о хороших чарах.",
    "До победы над первым боссом кампании ваш уровень ограничен десятым.",
    "Не пытайтесь фармить таланты и опыт на мобофермах — там стоят ограничения. Лучший способ расти — проходить кампанию и бить боссов.",
    "Трофеи из Пепельного Камня позволяют создать очень полезные предметы: компас, указывающий на структуры, или жезл, что легко возводит сложные постройки.",
]

# ══ метки главного меню ═════════════════════════════════════════════
# Версии модов и служебные значения намеренно не переводятся.
LABELS = {
    '&e★&r Official Wiki':            '&e★&r Официальная вики',
    'Continue':                       'Продолжить',
    'Cosmetics':                      'Косметика',
    'Create Server':                  'Создать сервер',
    'Disconnect':                     'Отключиться',
    'Get 25% OFF with Bisect Hosting': 'Скидка 25% на Bisect Hosting',
    'Multiplayer':                    'Сетевая игра',
    'Server Browser':                 'Список серверов',
    'Share World':                    'Открыть мир для сети',
    'Singleplayer':                   'Одиночная игра',
    'Start Journey':                  'Начать путь',
    'Teleport to The Timekeep':        'Телепорт в Цитадель Времени',
    'Video Tutorial':                 'Видеоруководство',
}

report = {}

# ══ 1. Puffish Skills ═══════════════════════════════════════════════
spans = json.load(open('puffish_spans_ru.json', encoding='utf-8'))
# longest-match-first, иначе короткая фраза съест часть длинной
ordered = sorted(spans.items(), key=lambda x: -len(x[0]))

# Пост-обработка склеек. Разрезание фраз по границам §-кодов не даёт
# переводчику построить связную грамматику там, где имя артефакта стоит
# посреди предложения: получается «Урон от Ледяная Скорбь». Здесь склейки
# переписываются так, чтобы имя в именительном падеже читалось естественно.
# Замены затрагивают только русский текст — §-коды и глифы не трогаются.
POSTFIX = [
    # обороты с именем артефакта: переводим в конструкцию с опорным словом
    ('Увеличивает урон ваших способностей школы:  ',
     'Увеличивает урон ваших способностей из книги заклинаний '),
    ('§7 книги заклинаний.', '§7.'),
    ('Пока эта способность снаряжена, вы накапливаете заряды:  ',
     'Пока эта способность снаряжена, вы получаете заряд эффекта '),
    ('пассивно накапливает заряды:  ', 'пассивно накапливает заряды эффекта '),
    ('Увеличивает максимум зарядов:  ', 'Увеличивает максимум зарядов эффекта '),
    ('Сливает воедино демоническую силу оружия:  ',
     'Сливает воедино демоническую силу клинка '),
    ('увеличивая стихийный урон оружия:  ', 'увеличивая стихийный урон клинка '),
    ('Дайте обет силе оружия:  ', 'Посвятите силу клинка '),
    ('Высвободите тьму оружия:  ', 'Высвободите тьму клинка '),
    ('Направьте мощь оружия:  ', 'Направьте мощь клинка '),
    ('Ваша связь с оружием:  ', 'Ваша связь крепнет: '),
    ("Позволяет §cФир'алат §7чтобы направлять Порчу",
     "Наполняет §cФир'алат §7Порчей"),
    ('Урон от  ', 'Урон оружия: '),
    ('превращая его в  ', 'превращая его в '),
]

DBL = re.compile(r'  +(§)')

def tr_string(s):
    for a, b in ordered:
        if a in s:
            s = s.replace(a, b)
    for a, b in POSTFIX:
        if a in s:
            s = s.replace(a, b)
    # схлопываем двойные пробелы перед §-кодом, оставшиеся после склейки
    s = DBL.sub(r' \1', s)
    return s

def walk(o):
    if isinstance(o, dict):
        return {k: (tr_string(v) if k in ('title', 'description', 'name')
                    and isinstance(v, str) else walk(v))
                for k, v in o.items()}
    if isinstance(o, list):
        return [walk(x) for x in o]
    return o

n_files = 0
for path in sorted(glob.glob(f'{SRC}/config/puffish_skills/**/*.json', recursive=True)):
    rel = os.path.relpath(path, SRC)
    dst = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    raw = open(path, encoding='utf-8').read()
    try:
        data = json.loads(raw)
    except Exception:
        shutil.copy2(path, dst)      # не JSON — копируем как есть
        continue
    json.dump(walk(data), open(dst, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    n_files += 1
report['puffish_files'] = n_files

# ══ 2. tips.txt ═════════════════════════════════════════════════════
# читаем побайтово: в текстовом режиме Python сам схлопнул бы CRLF в LF,
# и мы бы записали файл с другими переводами строк, чем в оригинале
raw_tips = open(f'{SRC}/config/fancymenu/assets/tips.txt', 'rb').read()
crlf = '\r\n' if b'\r\n' in raw_tips else '\n'
src_tips = raw_tips.decode('utf-8')
n_src = len([l for l in src_tips.replace('\r\n', '\n').split('\n') if l.strip()])
assert n_src == len(TIPS), f'подсказок в исходнике {n_src}, в переводе {len(TIPS)}'
dst = os.path.join(OUT, 'config/fancymenu/assets/tips.txt')
os.makedirs(os.path.dirname(dst), exist_ok=True)
open(dst, 'w', encoding='utf-8', newline='').write(crlf.join(TIPS))
report['tips'] = len(TIPS)

# ══ 3. метки меню FancyMenu ═════════════════════════════════════════
lab_re = re.compile(r'^(\s*label\s*=\s*)(.*?)(\s*)$')
n_lab = 0
n_lay = 0
for path in sorted(glob.glob(f'{SRC}/config/fancymenu/customization/*.txt')):
    rel = os.path.relpath(path, SRC)
    dst = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    changed = False
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    for i, line in enumerate(lines):
        m = lab_re.match(line)
        if m and m.group(2) in LABELS:
            lines[i] = m.group(1) + LABELS[m.group(2)] + m.group(3)
            n_lab += 1
            changed = True
    open(dst, 'w', encoding='utf-8').write('\n'.join(lines))
    if changed:
        n_lay += 1
report['labels'] = n_lab
report['layouts'] = n_lay

# ══ 4. pack.mcmeta ресурспака ═══════════════════════════════════════
mcmeta = {
    "pack": {
        "pack_format": 15,
        "description": "§6Prominence II: Hasturian Era §f— русская локализация"
    }
}
os.makedirs(f'{OUT}/resourcepack', exist_ok=True)
json.dump(mcmeta, open(f'{OUT}/resourcepack/pack.mcmeta', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)

# ══ отчёт ═══════════════════════════════════════════════════════════
print('Собрано:')
print(f"  Puffish Skills, файлов JSON:      {report['puffish_files']}")
print(f"  Подсказок загрузки:               {report['tips']}")
print(f"  Меток меню заменено:              {report['labels']} в {report['layouts']} макетах")
print(f"  Глав квестбука:                   "
      f"{len(glob.glob(f'{OUT}/config/ftbquests/quests/chapters/*.snbt'))}")
print(f"  pack_format ресурспака:           15")
