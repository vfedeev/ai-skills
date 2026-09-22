#!/usr/bin/env python3
"""Однопроходный конвейер text-parser-ru: сырой txt -> чистый txt (+docx) + отчёт.

Заменяет цепочку из 4-6 отдельных прогонов (нормализация -> ТИПО -> пост-правила ->
регресс-чек -> docx). Весь цикл — ОДИН вызов:

  python3 pipeline.py raw.txt profile.py out-prefix [--attach-short] [--docx] [--profile-only]

profile.py — профиль класса задач (см. references/patterns.md, «Как копить»):
  run(t) -> (t, stats)            правила, выведенные из эталона (ОБЯЗАТЕЛЬНО)
  CHECKS = {name: regex}          нуль-паттерны: после чистки вхождений быть не должно
необязательно:
  POST(t) -> (t, stats)           пост-обработка ПОСЛЕ ТИПО-пресета (напр. склейка
                                  NBSP в «ёлочках» — она не может идти до кавычек)
  HOME_STYLE = {"dashes": False, "dates_blank": regex}
                                  отключение шагов пресета и «ровно один пустой
                                  абзац перед каждой датой-строкой»

Порядок: base-нормализация (BOM/CR/¶/soft hyphen/дефис-переносы — только вёрстка,
не смысл) -> run(profile) -> ТИПО (quotes, [dashes], spaces, attach-short по флагу)
-> POST -> даты-отбивки -> регресс-чек -> запись out-prefix--clean.txt (+ docx).
Exit code 1 = какой-то нуль-чек провален, результат НЕ сдавать.
"""
import argparse
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clean_text
import typo_ru


def base_pre(text):
    rep = {}
    def sub(name, pat, repl):
        nonlocal text
        text, n = re.subn(pat, repl, text)
        if n:
            rep[name] = n
    sub("bom", "\ufeff", "")
    sub("crlf", "\r\n", "\n")
    sub("cr", "\r", "\n")
    sub("pilcrow", "\u00b6", "")
    sub("softhyphen", "\u00ad", "")
    sub("zerowidth", "[\u200b-\u200f]", "")
    sub("hyphen-join", "-\n(?=[\u0430-\u044f\u0451a-z])", "")
    return text, rep


def ensure_date_blanks(text, date_re, blank=1):
    """Перед каждой строкой-датой: ровно `blank` пустых абзацев (blank=1 ->
    gap из blank+1 пустых строк). Лишние пустые до даты выкидываются, ведущая
    пустота файла не появляется."""
    dpat = re.compile(date_re + r"$")
    out = []
    for ln in text.split("\n"):
        if dpat.match(ln.strip()) and ln.strip():
            while out and not out[-1].strip():
                out.pop()
            if out:
                out.extend([""] * (blank + 1))
        out.append(ln)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("profile")
    ap.add_argument("prefix")
    ap.add_argument("--attach-short", action="store_true")
    ap.add_argument("--docx", action="store_true")
    ap.add_argument("--profile-only", action="store_true",
                    help="пропустить ТИПО-пресет (если профиль его не требует)")
    a = ap.parse_args()

    spec = importlib.util.spec_from_file_location("profile", a.profile)
    prof = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prof)
    home = getattr(prof, "HOME_STYLE", {})

    stats = {}
    text, pre = base_pre(open(a.raw, encoding="utf-8").read())
    stats["pre"] = pre

    text, s1 = prof.run(text)
    stats.update(s1)

    if not a.profile_only:
        report = []
        text = typo_ru.fix_quotes(text, report)
        if report:
            stats["typo-report"] = report
        if home.get("dashes", True):
            text = typo_ru.fix_dashes(text)
        text = typo_ru.fix_spaces(text)
        if a.attach_short:
            text = typo_ru.attach_short(text)

    if hasattr(prof, "POST"):
        text, s2 = prof.POST(text)   # contract: POST(t) -> (t, stats)
        stats.update(s2)

    if home.get("dates_blank"):
        text = ensure_date_blanks(text, home["dates_blank"])
        stats["date-blanks"] = len(re.findall(r"(?m)^" + home["dates_blank"] + r"$", text))

    checks = {name: len(re.findall(pat, text))
              for name, pat in getattr(prof, "CHECKS", {}).items()}
    bad = {k: v for k, v in checks.items() if v}

    out = a.prefix + "--clean.txt"
    open(out, "w", encoding="utf-8").write(text)
    if a.docx:
        import build_docx_schedule
        sys.argv = ["build_docx_schedule", out, a.prefix + ".docx",
                    home.get("docx_bold", "")]
        build_docx_schedule.main()

    print(json.dumps({"clean": out, "stats": stats, "checks": checks,
                      "regression": "FAIL" if bad else "OK",
                      **({"failed": bad} if bad else {})}, ensure_ascii=False))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
