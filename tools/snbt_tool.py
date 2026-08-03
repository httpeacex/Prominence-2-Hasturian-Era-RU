#!/usr/bin/env python3
"""
Извлечение и обратная вставка переводимых строк в SNBT-файлы FTB Quests.

Работает по байтовым смещениям: каждая строка запоминается как
(файл, начало, конец), поэтому обратная вставка идёт с конца файла
и не сдвигает позиции остальных строк. Формат SNBT не парсится
целиком — это сознательно, чтобы не потерять форматирование,
комментарии и порядок ключей автора сборки.
"""
import json, os, re, sys, hashlib, glob

# Поля SNBT, содержащие текст для игрока
FIELDS = ("title", "subtitle", "description", "text", "hover")
FIELD_RE = re.compile(
    r'(?<![A-Za-z_])(' + "|".join(FIELDS) + r')\s*:\s*',
    re.IGNORECASE,
)


def find_strings(src):
    """Возвращает список (start, end, value) для всех строковых литералов
    в переводимых полях. end указывает на закрывающую кавычку включительно."""
    out = []
    for m in FIELD_RE.finditer(src):
        i = m.end()
        if i >= len(src):
            continue
        if src[i] == '[':
            # список строк — идём до закрывающей скобки на нулевой глубине
            depth = 0
            j = i
            while j < len(src):
                c = src[j]
                if c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0:
                        break
                elif c == '"':
                    s, e, v = read_string(src, j)
                    out.append((s, e, v))
                    j = e
                j += 1
        elif src[i] == '"':
            s, e, v = read_string(src, i)
            out.append((s, e, v))
    return out


def read_string(src, start):
    """Читает строковый литерал начиная с кавычки на позиции start.
    Возвращает (start, end_inclusive, decoded_value)."""
    assert src[start] == '"'
    j = start + 1
    buf = []
    while j < len(src):
        c = src[j]
        if c == '\\':
            nxt = src[j + 1] if j + 1 < len(src) else ''
            buf.append({'n': '\n', 't': '\t', 'r': '\r'}.get(nxt, nxt))
            j += 2
            continue
        if c == '"':
            return start, j, ''.join(buf)
        buf.append(c)
        j += 1
    return start, len(src) - 1, ''.join(buf)


def encode(value):
    """Кодирует строку обратно в SNBT-литерал."""
    v = (value.replace('\\', '\\\\')
              .replace('"', '\\"')
              .replace('\n', '\\n')
              .replace('\t', '\\t')
              .replace('\r', '\\r'))
    return '"' + v + '"'


def sid(value):
    """Стабильный идентификатор строки — хэш от содержимого.
    Одинаковый текст в разных главах получает один id, поэтому
    перевод не дублируется."""
    return hashlib.sha1(value.encode('utf-8')).hexdigest()[:12]


def cmd_extract(quest_dir, out_json):
    index = {}      # id -> {"en": str, "hits": int, "files": [...]}
    per_file = {}   # относительный путь -> число строк
    for path in sorted(glob.glob(os.path.join(quest_dir, '**', '*.snbt'), recursive=True)):
        src = open(path, encoding='utf-8', errors='replace').read()
        rel = os.path.relpath(path, quest_dir)
        n = 0
        for s, e, v in find_strings(src):
            if not v.strip():
                continue
            k = sid(v)
            rec = index.setdefault(k, {"en": v, "hits": 0, "files": []})
            rec["hits"] += 1
            if rel not in rec["files"]:
                rec["files"].append(rel)
            n += 1
        per_file[rel] = n
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    total = sum(per_file.values())
    print(f"Файлов: {len(per_file)}  вхождений: {total}  уникальных: {len(index)}")
    print(f"Символов уникальных: {sum(len(r['en']) for r in index.values())}")
    print("\nПо файлам (топ-20 по объёму текста):")
    sizes = {}
    for k, r in index.items():
        for fl in r["files"]:
            sizes[fl] = sizes.get(fl, 0) + len(r["en"])
    for fl, c in sorted(sizes.items(), key=lambda x: -x[1])[:20]:
        print(f"  {c:>7}  {per_file.get(fl,0):>4} строк  {fl}")


def cmd_inject(quest_dir, ru_json, out_dir):
    ru = json.load(open(ru_json, encoding='utf-8'))
    applied = missing = 0
    for path in sorted(glob.glob(os.path.join(quest_dir, '**', '*.snbt'), recursive=True)):
        src = open(path, encoding='utf-8', errors='replace').read()
        rel = os.path.relpath(path, quest_dir)
        spans = [x for x in find_strings(src) if x[2].strip()]
        # с конца, чтобы смещения не поехали
        for s, e, v in sorted(spans, key=lambda x: -x[0]):
            k = sid(v)
            tr = ru.get(k)
            if isinstance(tr, dict):
                tr = tr.get('ru')
            if not tr:
                missing += 1
                continue
            src = src[:s] + encode(tr) + src[e + 1:]
            applied += 1
        dst = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'w', encoding='utf-8').write(src)
    print(f"Заменено вхождений: {applied}  без перевода: {missing}")


def cmd_split(en_json, out_dir, parts):
    """Делит словарь на N частей примерно равного объёма символов,
    сохраняя группировку по файлам — так переводчик видит связный контекст."""
    en = json.load(open(en_json, encoding='utf-8'))
    # группируем по первому файлу
    groups = {}
    for k, r in en.items():
        groups.setdefault(r["files"][0], []).append((k, r))
    ordered = sorted(groups.items(), key=lambda x: -sum(len(r["en"]) for _, r in x[1]))
    buckets = [[] for _ in range(parts)]
    weights = [0] * parts
    for fl, items in ordered:
        i = weights.index(min(weights))
        buckets[i].extend(items)
        weights[i] += sum(len(r["en"]) for _, r in items)
    os.makedirs(out_dir, exist_ok=True)
    for i, b in enumerate(buckets, 1):
        d = {k: r["en"] for k, r in b}
        p = os.path.join(out_dir, f"part{i}.json")
        json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"part{i}.json  строк: {len(d):>5}  символов: {weights[i-1]:>7}")


def cmd_lint(en_json, ru_json):
    """Проверяет, что число спецификаторов формата и коды цвета совпадают."""
    en = json.load(open(en_json, encoding='utf-8'))
    ru = json.load(open(ru_json, encoding='utf-8'))
    spec = re.compile(r'%(?:\d+\$)?[sdf]|%%')
    bad = []
    for k, tr in ru.items():
        if isinstance(tr, dict):
            tr = tr.get('ru', '')
        src = en.get(k)
        src = src["en"] if isinstance(src, dict) else src
        if src is None:
            continue
        a, b = len(spec.findall(src)), len(spec.findall(tr))
        if a != b:
            bad.append((k, a, b, src[:60], tr[:60]))
    if bad:
        print(f"ОШИБКИ спецификаторов: {len(bad)}")
        for k, a, b, s, t in bad[:30]:
            print(f"  {k}  en={a} ru={b}\n    EN: {s}\n    RU: {t}")
    else:
        print(f"Спецификаторы в порядке. Проверено строк: {len(ru)}")


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'extract':
        cmd_extract(sys.argv[2], sys.argv[3])
    elif c == 'inject':
        cmd_inject(sys.argv[2], sys.argv[3], sys.argv[4])
    elif c == 'split':
        cmd_split(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    elif c == 'lint':
        cmd_lint(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
