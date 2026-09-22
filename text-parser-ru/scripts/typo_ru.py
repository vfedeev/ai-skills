#!/usr/bin/env python3
"""Пресет ТИПО: русская типографика по правилам (Русская типографика / ГОСТ 7.5).

Три операции, содержимое не трогает:
  1. кавычки: "..." -> «...», вложенные '...' -> „...“; “...” нормализуются.
     Незакрытые кавычки НЕ угадываются: количество — в отчёт (в список вопросов).
  2. тире: " - ", " -- " между словами -> " — "; "5 - 7" -> "5–7" (диапазон);
     "..." -> "…". Дефис внутри слова и "- " в начале строки (маркер) не трогает.
  3. пробелы: убрать перед , . ; : ! ? % ) ] и после ( [ ; схлопнуть двойные.

Флаг --attach-short: однобуквенные предлоги/союзы и частицы (в, с, у, бы, ли, же…)
приклеиваются неразрывным пробелом. По умолчанию выкл.

Использование: python3 typo_ru.py вход выход [--attach-short] [--audit]
"""
import argparse
import difflib
import re

INCH = "\ue000"   # защита дюймов: 5"
APOS = "\ue001"   # защита апострофа в слове: O'Brien
# ВАЖНО: W — это СЫРОЕ СОДЕРЖИМОЕ класса без скобок. Никогда не оборачивать
# [{W}] — вложенный класс [[...]] молча матчит литеральные скобки (баг, ловился 2раза).
W = r"\w\u0430-\u044f\u0451"


def fix_quotes(text, report):
    text = re.sub(r"(?<=\d)\s*\"", INCH, text)
    text = re.sub(rf"(?<=[{W}])'(?=[{W}])", APOS, text)
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")

    def outer(m):
        inner = re.sub(r"'([^'\n]*)'",
                       lambda mm: "\u201e" + mm.group(1) + "\u201c", m.group(1))
        return "\u00ab" + inner + "\u00bb"

    text, n = re.subn(r"\"([^\"\n]*)\"", outer, text)
    left = text.count('"')
    if left:
        report.append(f'кавычек " без пары: {left} — не тронуто, идут в вопросы')
    return text.replace(INCH, '"').replace(APOS, "'")


def fix_dashes(text):
    # диапазоны чисел/времени: любое тире-подобное между цифрами -> en dash без пробелов
    text = re.sub(r"(?<=\d)[ \t]*[-\u2013\u2014][ \t]*(?=\d)", "\u2013", text)
    # разделитель-тире между словами -> em dash с пробелами; справа/слева могут
    # стоять кавычки заголовков («Название» - Описание)
    text = re.sub(rf"(?<=[{W}\u00bb])[ \t]+[-\u2013][ \t]+(?=[{W}\u00ab\u201e])", " \u2014 ", text)
    text = re.sub(rf"(?<=[{W}])[ \t]+--[ \t]+(?=[{W}])", " \u2014 ", text)
    return re.sub(r"(?<!\.)\.\.\.(?!\.)", "\u2026", text)


def fix_spaces(text):
    text = re.sub(r"[ \t]+([,.;:!?%)\]])", r"\1", text)
    text = re.sub(r"([\[(]) +", r"\1", text)
    text = re.sub(r"\u00ab[ \t]+", "\u00ab", text)
    text = re.sub(r"[ \t]+\u00bb", "\u00bb", text)
    text = re.sub(r"[\u00ab\u201e][ \t]+", lambda m: m.group(0)[0], text)
    return re.sub(r"(?<=\S)[ ]{2,}(?=\S)", " ", text)


SHORT_WORDS = ["\u0432", "\u0441", "\u0443", "\u043a", "\u043d", "\u043e", "\u043f", "\u0431",
               "\u043b", "\u043c", "\u0442", "\u0438", "\u0430", "\u044e", "\u044f", "\u0439",
               "\u0436", "\u0447", "\u0431\u044b", "\u043b\u0438", "\u0436\u0435", "\u043c\u043d\u0435", "\u0432\u0435\u0434\u044c"]


def attach_short(text):
    # пробел/consume внутри паттерна, а не lookahead: иначе NBSP вставляется
    # ДО пробела и получается двойной
    pat = re.compile(r"(?<![\w-])(" + "|".join(SHORT_WORDS) + r")[ \u00a0]+",
                     re.IGNORECASE | re.UNICODE)
    return pat.sub(lambda m: m.group(1) + "\u00a0", text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--attach-short", action="store_true")
    ap.add_argument("--audit", action="store_true")
    a = ap.parse_args()

    text0 = open(a.raw, encoding="utf-8").read()
    report = []
    t = fix_quotes(text0, report)
    t = fix_dashes(t)
    t = fix_spaces(t)
    if a.attach_short:
        t = attach_short(t)

    n_changed = sum(1 for line in difflib.unified_diff(
        text0.split("\n"), t.split("\n"), n=0)
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
    print(f"строк изменено: {n_changed}")
    for r in report:
        print("!", r)
    if a.audit:
        return
    if not a.out:
        raise SystemExit("нужен путь out или --audit")
    open(a.out, "w", encoding="utf-8").write(t)
    print(f"записан {a.out}")


if __name__ == "__main__":
    main()
