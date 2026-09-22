#!/usr/bin/env python3
"""Пресет CJK: чистка текста от иероглифов и азиатской пунктуации.

Без флагов = АУДИТ (ничего не пишет): счётчики по группам Unicode, проблемные
строки, проверка на mojibake. С флагами:
  --map     полноширинные/CJK-знаки -> обычные (безопасно, письма не трогает)
  --remove  удалить иероглифы/кану/хангыль + подчищать висячие пробелы

Порядок: --map всегда раньше --remove (сначала спасаем знаки, потом режем письмена).
Содержательные иероглифы (бренд, имя, цитата) remove не спрашивает: смотри аудит
и решай вместе с пользователем.
"""
import argparse
import re

GROUPS = {
    "cjk-ideographs": "[\\u4e00-\\u9fff\\u3400-\\u4dbf\\uf900-\\ufaff]",
    "kana": "[\\u3040-\\u30ff]",
    "hangul": "[\\uac00-\\ud7af\\u1100-\\u11ff\\u3130-\\u318f]",
    "cjk-punct": "[\\u3000-\\u303f\\uff01-\\uff0f\\uff1a-\\uff20\\uff3b-\\uff40\\uff5b-\\uff65]",
    "fullwidth-latin": "[\\uff21-\\uff3a\\uff41-\\uff5a\\uff10-\\uff19]",
}

# CJK-пунктуация и полноширинные -> обычные
MAP = {
    "\u3000": " ", "\u3001": ",", "\u3002": ".", "\uff0c": ",", "\uff0e": ".",
    "\uff1a": ":", "\uff1b": ";", "\uff1f": "?", "\uff01": "!",
    "\uff08": "(", "\uff09": ")", "\uff3b": "[", "\uff3d": "]",
    "\u300a": "\u00ab", "\u300b": "\u00bb", "\u300c": "\u00ab", "\u300d": "\u00bb",
    "\u3010": "[", "\u3011": "]", "\uff02": '"', "\uff07": "'",
    "\u00b7": "", "\u30fb": "", "\u2027": "",
}
# ВАЖНО: альтернация групп, не конкатенация: [..][..] — это ПОСЛЕДОВАТЕЛЬНОСТЬ
# трёх символов, а не множество. Прошло тест на реальном смешанном тексте.
SCRIPT_RE = re.compile(
    GROUPS["cjk-ideographs"] + "|" + GROUPS["kana"] + "|" + GROUPS["hangul"])


def moji_check(text):
    """Похоже ли на битую кодировку (mojibake), а не на настоящие иероглифы."""
    try:
        fixed = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None
    cyr = lambda s: sum("\u0430" <= c <= "\u044f" or c in "\u0410\u042f\u0401\u0451" for c in s)
    return fixed if cyr(fixed) > 3 * max(1, cyr(text)) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--map", dest="map_", action="store_true")
    ap.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    text = open(a.raw, encoding="utf-8").read()

    pats = {k: re.compile(v) for k, v in GROUPS.items()}
    counts = {k: len(p.findall(text)) for k, p in pats.items()}
    for k, n in counts.items():
        if n:
            print(f"{k}: {n}")
    if not any(counts.values()):
        print("попаданий нет")

    m = moji_check(text)
    if m:
        print("MOJIBAKE?: похоже на битую кодировку (latin-1 -> utf-8 читается по-русски)."
              " Не удаляй --remove; спроси пользователя. Пример: " + m[:80])

    hits = [(i + 1, ln.strip()) for i, ln in enumerate(text.split("\n"))
            if any(p.search(ln) for p in pats.values())]
    for i, ln in hits[:15]:
        print(f"  строка {i}: {ln[:100]}")
    if len(hits) > 15:
        print(f"  ...ещё {len(hits) - 15} строк")

    if not (a.map_ or a.remove):
        print("аудит без изменений; применяй --map / --remove осознанно")
        return

    if not a.out:
        raise SystemExit("нужен путь out или только аудит (без флагов)")

    stats = {}
    if a.map_:
        out_chars = []
        for c in text:
            if c in MAP:
                out_chars.append(MAP[c])
            elif "\uff01" <= c <= "\uff5e":
                out_chars.append(chr(ord(c) - 0xfee0))
            else:
                out_chars.append(c)
        mapped = sum(1 for x, y in zip(text, out_chars) if x != y)
        text = "".join(out_chars)
        stats["map"] = mapped
    if a.remove:
        text, n = SCRIPT_RE.subn("", text)
        stats["remove-scripts"] = n
        text = re.sub(r"[ ]{2,}", " ", text)
        text = re.sub(r"[ ]+([,.;:!?\)\]])", r"\1", text)
        text = re.sub(r"([(\[]) +", r"\1", text)
        text = re.sub(r"[ \t]+\n", "\n", text)  # хвостовые пробелы: строка состояла из письма
    print("изменения:", stats)
    open(a.out, "w", encoding="utf-8").write(text)
    print(f"записан {a.out}")


if __name__ == "__main__":
    main()
