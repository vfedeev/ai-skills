#!/usr/bin/env python3
"""Сборка .docx из txt с сохранением абзацной структуры (УНИВЕРСАЛЬНЫЙ конвертер,
не только для расписаний): пустая строка = абзац (¶), переводы внутри блока =
мягкие переносы (Shift+Enter / <w:br/>). Word-семантика переноса текста в docx.

Использовать когда: результат должен нести структуру абзацев, которую txt
не перевозит (см. шаг 5 SKILL.md). NBSP/тире внутри текста сохраняются как
есть — оформляй их до этого шага (пресеты/правила из эталона).
Имена файлов через -- (Windows-safe).

Использование: python3 build_docx_schedule.py вход.txt выход.docx [BOLD_REGEX]
BOLD_REGEX — необязательный: строки (и переводы внутри абзаца), матвящие его,
жирным — например '^\\d{{1,2}}:\\d{{2}}' — время; строки мероприятий с временем.
"""
import re
import sys
import zipfile

CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/word/document.xml" '
      'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
      '</Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
        ' Target="word/document.xml"/></Relationships>')
DOC_TPL = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           '<w:body>%s</w:body></w:document>')


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    # опция: 3-й аргумент — regex; строки (в т.ч. переводы внутри блока),
    # матвящие его, выводятся жирным (<w:b/>)
    bold_re = re.compile(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else None
    text = open(src, encoding="utf-8").read().replace("\r\n", "\n")
    # пустые блоки -> пустой абзац <w:p/> (отбивка перед датой), подряд >1 -> один,
    # ведущая пустота выкидывается
    blocks = re.split(r"\n[ \t]*\n", text.strip())
    out, prev_empty = [], True
    BR = "<w:r><w:br/></w:r>"
    for b in blocks:
        is_empty = not any(x.strip() for x in b.split("\n"))
        if is_empty:
            if not prev_empty:
                out.append("")
            prev_empty = True
            continue
        prev_empty = False
        runs = []
        for x in b.split("\n"):
            rpr = "<w:rPr><w:b/></w:rPr>" if (bold_re and bold_re.search(x)) else ""
            runs.append(f'<w:r>{rpr}<w:t xml:space="preserve">{esc(x)}</w:t></w:r>')
        out.append("<w:p>" + BR.join(runs) + "</w:p>")
    body = [x if x else "<w:p/>" for x in out]
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", DOC_TPL % "".join(body))
    nl = chr(10)
    print(f"абзацев(¶): {len(body)}, пустых(отбивок): {sum(1 for x in out if not x)}, "
          f"переносов(↵): {sum(len(b.split(nl)) - 1 for b in out if b)} -> {dst}")


if __name__ == "__main__":
    main()
