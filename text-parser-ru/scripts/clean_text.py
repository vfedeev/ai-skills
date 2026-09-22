#!/usr/bin/env python3
"""Каркас чистильщика текста для text-parser-ru.

Не «универсальный очиститель»: конкретные правила всегда заполняются по эталону
пользователя. Скрипт даёт безопасную инфраструктуру: сырой вход остаётся нетронутым,
каждое правило считается и логируется, непойманные подозрительные символы выводятся
отчётом, а не молча меняются.

Использование:
  python3 clean_text.py raw.txt out.txt --rules rules.py
где rules.py определяет RULES: list[tuple[name, regex_str|pattern, replacement]].
Без --rules применяются базовые безопасные правила — только для первичного
аудита (--audit), не для сдачи.
"""
import argparse
import collections
import re


def base_rules():
    """Безопасные по умолчанию: только явные мусорные символы, не трогают смысл."""
    return [
        ("strip-bom", re.compile(r"\ufeff"), ""),
        ("nbsp->space", re.compile(r"\u00a0"), " "),
        ("soft-hyphen", re.compile(r"\u00ad"), ""),
        ("zero-width", re.compile(r"[\u200b-\u200f]"), ""),
        ("para-mark-eol", re.compile(r"\s*[\u00b6\u00a7]\s*$", re.M), ""),
        ("collapse-space", re.compile(r"(?<=\S) {2,}(?=\S)"), " "),
    ]


def load_rules(path):
    ns = {}
    exec(open(path, encoding="utf-8").read(), ns)
    out = []
    for name, pat, repl in ns["RULES"]:
        out.append((name, re.compile(pat) if isinstance(pat, str) else pat, repl))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("out", nargs="?", help="не указывай при --audit")
    ap.add_argument("--rules", help="python-файл с RULES по эталону пользователя")
    ap.add_argument("--audit", action="store_true", help="только отчёт, без записи")
    a = ap.parse_args()

    text = open(a.raw, encoding="utf-8").read()
    # кастомные правила идут ПЕРВЫМИ: склейки строк должны видеть оригинальные
    # концы строк ("\n" сразу после текста), прежде чем базовые начнут чистить
    # ¶/пробелы и оставлять висячие " \n". Базовые — доборка в конце.
    rules = (load_rules(a.rules) if a.rules else []) + base_rules()
    stats = collections.OrderedDict()
    for name, pat, repl in rules:
        text, n = pat.subn(repl, text)
        stats[name] = n

    for name, n in stats.items():
        print(f"{name}: {n}")

    # отчёт об остатках, которые правила не покрыли: видно, а не потеряно
    leftovers = collections.Counter()
    ok = set("\n\t »—…ё“”‘’–•№")
    for ch in text:
        if ord(ch) > 0x2000 or (0x80 <= ord(ch) <= 0xff and ch not in ok):
            if ch not in ok:
                leftovers[ch] += 1
    if leftovers:
        print("Подозрительные символы в остатке (в список вопросов!):",
              {hex(ord(c)): n for c, n in leftovers.items()})
    if not a.audit:
        if not a.out:
            raise SystemExit("нужен путь out или --audit")
        open(a.out, "w", encoding="utf-8").write(text)
        print(f"записан {a.out}")


if __name__ == "__main__":
    main()
