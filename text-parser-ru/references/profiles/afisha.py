# -*- coding: utf-8 -*-
"""[класс: афиши/расписания] профиль ДОМ-СТИЛЬ Владимира (эталон Word 2026-09-22).

Диапазон: дефис без пробелов; разделитель: NBSP+–+NBSP; «ёлочки» склеены NBSP;
место отдельной строкой без скобок; перед датой ровно один пустой абзац.

Использование: python3 scripts/pipeline.py raw.txt profile_afisha.py out [--docx]

ОПЦИИ (выключены по умолчанию — включать только по явной просьбе пользователя,
правка 2026-09-22): OPTS["age_comma"] — «Каминный зал 4+» -> «Каминный зал, 4+»;
HOME_STYLE["docx_bold"] = regex — жирные строки (например время+название).
"""
import re

# переключатель по запросу: правки вносятся здесь (или env AFISHA_OPTS=age_comma)
import os
OPTS = {"age_comma": bool(os.environ.get("AFISHA_OPTS", "").count("age_comma"))}

VENUES = (r"(Ресторан|Каминный зал|Сбор у|Шат[ёе]р|Территория отеля|"
          r"Центральная [ёе]лка|Костровая зона|Ресепшн)")
VENUE = re.compile(r"\(" + VENUES + r"([^()]*)\)", re.IGNORECASE)
MONTHS = (r"января|февраля|марта|апреля|мая|июня|июля|августа|сентября|"
          r"октября|ноября|декабря")
TIME = r"\d{1,2}:\d{2}"
NBSP, EN = "\u00a0", "\u2013"

HOME_STYLE = {"dashes": False}  # em-между-слов в POST. docx_bold: вкл. по запросу,
# напр. HOME_STYLE["docx_bold"] = r"^\d{1,2}:\d{2}"


def run(t):
    stats = {}
    def apply(name, pat, repl, flags=0):
        nonlocal t
        t, n = re.subn(pat, repl, t, flags=flags)
        if n:
            stats[name] = n

    apply("time-dots", r"(?<![\d:])(\d{1,2})\.(\d{2})(?![\d:])", r"\1:\2")
    apply("paren-space", r"\(\s+", "(")
    # диапазон времени: любое тире между чч:чч -> простой дефис (ДОМ-СТИЛЬ)
    apply("range-hyphen", rf"({TIME})[ \t]*[-\u2013\u2014][ \t]*({TIME})", r"\1-\2")
    # разделитель «время — название»: любое тире/пусто -> NBSP–NBSP
    apply("sep", rf"({TIME})[ \t]*[-\u2013\u2014]?[ \t]+(?=\S)", rf"\1{NBSP}{EN}{NBSP}", flags=re.M)
    apply("sep-glued", rf"({TIME})(?=[^\d\s:,;.)\-\u2013\u2014{NBSP}])", rf"\1{NBSP}{EN}{NBSP}")
    # название после разделителя — с заглавной (если приклеено строчным)
    apply("capitalize", rf"(?m)^({TIME}[^{EN}\n]*{EN}[{NBSP} ]*)([а-яё])",
          lambda m: m.group(1) + m.group(2).upper())
    # наращение 1-ый/2-ой -> 1-й
    apply("ordinal", r"(?<=\d)-[ыо]й\b", "-й")
    # инлайн-место (+возраст) в конце строки -> на свою строку
    def split_inline(m):
        if not re.match(r"\(\s*" + VENUES, m.group(1), re.IGNORECASE):
            return m.group(0)
        return "\n" + m.group(1) + (m.group(2) or "")
    t, n = re.subn(r"(?<=\S)[ \t]+(\([^()\n]*\))([ \t]*\d+\+?)?[ \t]*$", split_inline, t, flags=re.M)
    if n:
        stats["venue-newline"] = n
    # скобки у названий мест снять, место с заглавной
    def ven(m):
        core = m.group(1)[0].upper() + m.group(1)[1:] + (m.group(2) or "")
        return core.rstrip()
    t, n = VENUE.subn(ven, t)
    if n:
        stats["unparen-venue"] = n
    apply("age", r"(?<=\d) \+(?!\d)", "+")
    if OPTS["age_comma"]:
        # по запросу: «Каминный зал 4+» -> «Каминный зал, 4+»
        apply("age-comma", r"(?m)^([А-ЯЁA-Z][^\n]*?[а-яёa-z]) (\d+\+?)$", r"\1, \2")
    apply("double-dot", r"\.\.(?!\.)", ".")
    apply("blank-ws", r"(?m)^[ \t]+$", "")
    apply("trailing-ws", r"[ \t]+\n", "\n")
    # blockify: строка со временем открывает блок; строка-дата = свой блок
    # с ОДНИМ пустым абзацем перед ним (\n{4} = пустой <w:p/> в docx);
    # прочие непустые строки = ↵ внутри блока. Пустые строки txt-вставки — артефакт.
    date_line = re.compile(rf"\d{{1,2}} {MONTHS}$")
    blocks = []  # list[list[str]]
    for ln in t.split("\n"):
        s = ln.strip()
        if not s:
            continue
        if date_line.match(s):
            blocks.append([s])
        elif re.match(TIME, s) or not blocks:
            blocks.append([s])
        else:
            blocks[-1].append(s)
    parts = []
    for k, b in enumerate(blocks):
        if k and date_line.match(b[0]):
            parts.append("\n\n\n\n")  # пустой абзац-отбивка перед датой
        elif k:
            parts.append("\n\n")
        parts.append("\n".join(b))
    t = "".join(parts)
    stats["blocks"] = len(blocks)
    return t, stats


def POST(t):
    """После ТИПО: em-тире между словами (аналог отключённого fix_dashes без
    задевания диапазонов), «ёлочки» склеиваются NBSP (дом-стиль).
    Возвращает (t, stats)."""
    stats = {}
    W = r"\w\u0430-\u044f\u0451"
    t, n = re.subn(rf"(?<=[{W}\u00bb])[ \t]+-[ \t]+(?=[{W}\u00ab\u201e])", " \u2014 ", t)
    if n:
        stats["word-em"] = n
    t, n = re.subn(r"\u00ab[^\u00bb\n]*\u00bb",
                   lambda m: m.group(0).replace(" ", NBSP), t)
    if n:
        stats["quote-nbsp"] = n
    return t, stats


CHECKS = {
    "time-dots-left": r"\d\.\d{2}(?![\d:])",
    "venue-paren": r"\((?:Ресторан|Каминный|Шат[ёе]р|Сбор у|Ресепшн|Территория|Центральная|Костровая)",
    "ordinal-long": r"\d-[ыо]й\b",
    "age-space": r"\d \+",
    "double-dot": r"\.\.(?!\.)",
    "double-blank": r"\n{5,}",  # 1 пустой абзац = \n\n\n\n — легален, 2+ — нет
    "lapki": r"\u201c|\u201d",
    "range-space-dash": rf"{TIME}[ \t]+[-{EN}\u2014][ \t]+{TIME}",
    "sep-single-nbsp": rf"{TIME}[ ]{EN}|{TIME}{EN}[ ]",
}
