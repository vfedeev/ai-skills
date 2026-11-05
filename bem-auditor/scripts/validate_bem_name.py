#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_bem_name.py — детерминированная проверка имён БЭМ-сущностей.

Правила взяты из:
  * bem.info/methodology/naming-convention (классическая схема + альтернативы)
  * getbem.com/naming (схема two-dashes)
  * habr.com/ru/articles/684170 (формализация классической схемы 7-ю правилами)

Использование:
  python3 validate_bem_name.py [--scheme classic|two-dashes] [--figma] NAME [NAME...]
  cat names.txt | python3 validate_bem_name.py --figma

Флаги:
  --scheme classic      классическая схема bem.info (по умолчанию)
  --scheme two-dashes   схема getbem.com (модификатор через --)
  --figma               добавлять поле auto_generated (имена автогенерации Figma)

Выход: JSON {scheme, total, valid_count, auto_generated_count,
             results:[{name, valid, errors[], warnings[], parsed{}}]}
Скрипт не падает на невалидных именах — они в JSON. Код возврата всегда 0.
Имена, начинающиеся с `-` или `_`, передавать после `--` (argparse).
"""
import argparse
import json
import re
import sys

LETTER = r"[a-z0-9]*[a-z][a-z0-9]*"  # в слове обязана быть хотя бы одна буква
WORD = r"{l}(?:-{l})*".format(l=LETTER)

CLASSIC_FULL = re.compile(
    r"^(?P<block>{w})(?:__(?P<element>{w}))?(?:_(?P<mod>{w})(?:_(?P<val>{w}))?)?$".format(w=WORD)
)
TD_FULL = re.compile(
    r"^(?P<block>{w})(?:__(?P<element>{w}))?(?:--(?P<mod>{w}))?$".format(w=WORD)
)

# исторические префиксы из до-БЭМовской эпохи Яндекса (bem.info/history)
LEGACY_PREFIX = re.compile(r"^(?:b|c|g|h|l|i|js)-")

# Figma-автоимена: <тип узла> + опциональный номер ("Frame 12", "Vector", "Union 3")
FIGMA_TYPES = {
    "frame", "group", "section", "rectangle", "ellipse", "line", "vector",
    "polygon", "star", "boolean", "booleanoperation", "union", "subtract",
    "intersect", "exclude", "slice", "image", "bitmap", "layer", "mask",
    "component", "componentset", "instance", "text", "artboard", "node",
    "svg", "pic", "after", "before",
}
FIGMA_NAME_RE = re.compile(r"^([A-Za-z]+)[\s_-]*(\d+)?$")


def is_figma_auto(name):
    m = FIGMA_NAME_RE.match(name.strip())
    if not m:
        return False
    return m.group(1).lower() in FIGMA_TYPES


def char_errors(name):
    """Ошибки по составу символов — общие для обеих схем."""
    errs = []
    if not name:
        return ["пустое имя"]
    if re.search(r"[\u0410-\u042f\u0430-\u044f\u0401\u0451]", name):
        errs.append("кириллица недопустима — имена пишутся латиницей")
    if re.search(r"[A-Z]", name):
        errs.append("заглавные буквы недопустимы (нижний регистр)")
    if re.search(r"[^0-9a-zA-Z\u0410-\u042f\u0430-\u044f\u0401\u0451_-]", name):
        errs.append("символы вне [a-z0-9_-]: пробелы, пунктуация и т.п. недопустимы")
    return errs


def parse_classic(name):
    errors, warnings = [], []

    errs = char_errors(name)
    if errs:
        return errs, warnings, None

    if name[0] in "-_" or name[-1] in "-_":
        errors.append("имя не может начинаться/заканчиваться разделителем")
    if "--" in name:
        errors.append("двойной дефис `--` — не классическая схема (это two-dashes/getbem)")
    if re.search(r"[_-]-|-_", name):
        errors.append("дефис и подчёркивание не могут соседствовать")
    if re.search(r"_{3,}", name):
        errors.append("подряд более двух подчёркиваний недопустимо")

    if name.count("__") > 1:
        errors.append("элемент элемента запрещён методологией (не более одного `__`)")

    first_single = None
    i = 0
    while i < len(name):
        if name.startswith("__", i):
            i += 2
            continue
        if name[i] == "_":
            first_single = i
            break
        i += 1
    dbl = name.find("__")
    if first_single is not None and dbl != -1 and first_single < dbl:
        errors.append("разделитель модификатора `_` не может стоять раньше `__`")

    if name.replace("__", "\0").count("_") > 2:
        errors.append("более двух `_`-разделителей (имя_модификатора_значение)")

    m = CLASSIC_FULL.match(name)
    if m is None:
        if not errors:
            errors.append("имя не соответствует классической схеме БЭМ")
        return errors, warnings, None

    parsed = {
        "block": m.group("block"),
        "element": m.group("element"),
        "modifier": m.group("mod"),
        "value": m.group("val"),
    }
    if parsed["value"] is not None:
        kind = "element-modifier(kv)" if parsed["element"] else "block-modifier(kv)"
    elif parsed["modifier"] is not None:
        kind = "element-modifier(bool)" if parsed["element"] else "block-modifier(bool)"
    elif parsed["element"] is not None:
        kind = "element"
    else:
        kind = "block"
    parsed["kind"] = kind

    if LEGACY_PREFIX.match(name):
        warnings.append("префикс `x-` — пережиток до-БЭМовской эпохи (bem.info/history); в современной схеме не используется")
    if parsed["element"] and parsed["element"] == parsed["block"]:
        warnings.append("имя элемента совпадает с именем блока — обычно признак лишнего уровня")
    return errors, warnings, parsed


def parse_two_dashes(name):
    errors, warnings = [], []

    errs = char_errors(name)
    if errs:
        return errs, warnings, None
    # в two-dashes `__` остаётся разделителем элемента (getbem.com),
    # недопустимо лишь одиночное `_` вне него
    if name.replace("__", "").find("_") != -1:
        errors.append("одиночное `_` вне `__`: в two-dashes модификатор отделяется только `--`")
    if name.count("--") > 1:
        errors.append("более одного `--` (модификатор может быть один)")
    if name.count("__") > 1:
        errors.append("элемент элемента запрещён (не более одного `__`)")
    i, j = name.find("--"), name.find("__")
    if i != -1 and j != -1 and i < j:
        errors.append("`--` модификатора не может стоять раньше `__` элемента")

    m = TD_FULL.match(name)
    if m is None:
        if not errors:
            errors.append("имя не соответствует схеме two-dashes")
        return errors, warnings, None

    parsed = {
        "block": m.group("block"),
        "element": m.group("element"),
        "modifier": m.group("mod"),
        "value": None,
    }
    if parsed["modifier"] is not None:
        kind = "element-modifier" if parsed["element"] else "block-modifier"
    elif parsed["element"] is not None:
        kind = "element"
    else:
        kind = "block"
    parsed["kind"] = kind
    if LEGACY_PREFIX.match(name):
        warnings.append("префикс `x-` — архаика, в современных схемах не используется")
    return errors, warnings, parsed


PARSERS = {"classic": parse_classic, "two-dashes": parse_two_dashes}


def main():
    ap = argparse.ArgumentParser(
        description="Валидация имён БЭМ-сущностей (классическая и two-dashes схемы).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--scheme", choices=list(PARSERS), default="classic")
    ap.add_argument("--figma", action="store_true",
                    help="добавлять поле auto_generated (автоимена Figma)")
    ap.add_argument("names", nargs="*")
    args = ap.parse_args()

    names = list(args.names)
    if not sys.stdin.isatty():
        names += [ln.strip() for ln in sys.stdin if ln.strip()]
    if not names:
        print(json.dumps({"error": "no names given"}, ensure_ascii=False))
        sys.exit(0)

    parser = PARSERS[args.scheme]
    results = []
    for name in names:
        errors, warnings, parsed = parser(name)
        item = {"name": name, "valid": not errors, "errors": errors, "warnings": warnings}
        if parsed:
            item["parsed"] = parsed
        if args.figma:
            item["auto_generated"] = is_figma_auto(name)
        results.append(item)

    print(json.dumps({
        "scheme": args.scheme,
        "total": len(results),
        "valid_count": sum(1 for r in results if r["valid"]),
        "auto_generated_count": sum(1 for r in results if r.get("auto_generated")),
        "results": results,
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
