#!/usr/bin/env python3
"""Проверка дословной цитаты: fetch URL -> strip HTML -> grep фразы; evidence на диске.

Использование:
  python3 fetch_quote.py <URL> "<точная фраза>" [еще фраза ...]
  OPTIONAL env: QUOTE_DIR (куда класть evidence, по умолчанию ./quote-evidence)

Вывод: MATCH/MISS по каждой фразе + краткий контекст; exit 0 если все MATCH,
1 если хоть один MISS, 2 если страница не открылась (тогда статус UNKNOWN —
не снижать уверенность без rendered-перепроверки web_extract: JS-рендеринг
даёт ложный MISS, см. references/verification-recipes.md).

Никаких зависимостей кроме stdlib.
"""
import html
import os
import re
import sys
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

def strip_html(raw: str) -> str:
    txt = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    txt = html.unescape(txt)
    return re.sub(r"\s+", " ", txt).strip()

def norm(s: str) -> str:
    # ё->е, кавычки/тире схлопнуть, регистр — нечувствительный к типографике греп
    s = s.replace("\u0451", "\u0435").lower()
    s = re.sub(r"[\u00ab\u00bb\u201c\u201d\"']", "", s)
    s = re.sub(r"[\u2013\u2014-]+", "-", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    url, phrases = sys.argv[1], sys.argv[2:]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        print(f"FETCH-FAIL {url}: {exc}\n=> статус факта остаётся UNKNOWN, не REFUTED")
        return 2
    text = strip_html(raw)
    low = norm(text)
    d = os.environ.get("QUOTE_DIR", "./quote-evidence")
    os.makedirs(d, exist_ok=True)
    slug = re.sub(r"[^\w.-]+", "_", url)[:80]
    ev = os.path.join(d, slug + ".txt")
    with open(ev, "w", encoding="utf-8") as f:
        f.write(f"SOURCE: {url}\n\n{text}")
    print(f"evidence: {ev}")
    rc = 0
    for p in phrases:
        np = norm(p)
        i = low.find(np)
        if i >= 0:
            j = text.lower().find(np[:20]) if len(np) >= 20 else i
            snippet = text[max(0, j - 60): j + len(p) + 60] if j >= 0 else text[:120]
            print(f"MATCH: {p!r}")
            print(f"  ...{snippet.strip()}...")
        else:
            rc = max(rc, 1)
            print(f"MISS : {p!r}  (для SPA/help-центров — перепроверь rendered web_extract)")
    return rc

if __name__ == "__main__":
    sys.exit(main())
