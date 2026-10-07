---
name: obsidian-canvas
version: 0.1.0
author: Vladimir F (with Hermes)
license: MIT
description: "Картинки (URL/файлы) на .canvas Obsidian vault напрямую."
metadata:
  hermes:
    tags: [obsidian, canvas, syncthing, clipper]
    related_skills: [obsidian-vault-automation, obsidian]
---

# Obsidian Canvas — агентский клип (фаза 2 obs-canvas-clipper)

Запись картинок на `.canvas` vault напрямую через файловую систему — вариант для
агента, работающего на сервере с Syncthing-копией vault (Local REST API при этом
не нужен: он живёт на localhost пользовательской машины). Раскладка — рядовая
сетка: ряд до 1600px, gap 40, целевая высота ноды 300 (константы в начале
`scripts/canvas_cli.py`). Скилл — «агентская обёртка» того же ядра, что и в
Chrome-расширении Obsidian Canvas Clipper; константы и алгоритмы должны совпадать.

## When to Use / Когда триггерить

- «добавь картинку <url> на холст <имя>», «скинь эти картинки в canvas»;
- «собери мудборд/коллаж из N картинок на новом холсте»;
- любая задача «картинка → .canvas» от агента (расширение делает то же из браузера);
- НЕ для чтения canvas'ов (это `obsidian` скилл) и НЕ для REST-пути (это
  `obsidian-vault-automation`).

## Инструмент

`scripts/canvas_cli.py` — только stdlib (Pillow опционален: без него размеры
берутся из встроенных парсеров PNG/JPEG/GIF/BMP/WebP/SVG-заголовков).
Результат каждой команды — одна JSON-строка в stdout; человекочитаемое — stderr.
Коды выхода: 0 ок, 2 аргументы, 3 canvas (нет/битый/коллизия), 4 источник/сеть,
5 Syncthing занят (повторить позже).

```sh
SKILL=~/.hermes/skills/obsidian-canvas
# все холсты vault'а
python3 $SKILL/scripts/canvas_cli.py list
# картинка (URL ИЛИ локальный путь) → нода на существующий холст
python3 $SKILL/scripts/canvas_cli.py add "https://ex.com/a.png" --canvas "Boards/Идеи.canvas"
# → сразу на НОВЫЙ холст в корне vault
python3 $SKILL/scripts/canvas_cli.py add ./photo.jpg --new "Мудборд 07-10"
# пустой холст без картинок
python3 $SKILL/scripts/canvas_cli.py create "Мудборд 07-10"
```

Флаги `add`: `--folder` (дефолт `Canvas Inbox`), `--target-height` (дефолт 300),
`--vault` (дефолт — `$OBSIDIAN_VAULT`, иначе `~/Sync/ObsidianVault`),
`--max-attempts` (дефолт 3).

## Workflow

1. Пользователь называет холст в запросе → `list` → сопоставь имя (без `.canvas`,
   регистронезависимо, подстрока). Совпадений 0 или >1 — уточняющий вопрос со
   списком кандидатов; не угадывай. Пользователь сказал «создай новый» — `--new`.
2. Для каждой картинки — отдельный вызов `add` (одна нода за вызов; серия вызовов
   сама раскладывает ноды в ряд/сетку).
3. Ошибки: code 5 → подожди 2–3 с и повтори (Syncthing пишет файл); code 3
   «canvas не найден» → предложи `list`; code 4 → картинка недоступна (403/404,
   пустой ответ) — спроси другой источник. В ответе пользователю всегда сообщай,
   что легло (image, canvas, node id) или почему не легло.
4. После записи в sync-область chmod 644 проставляется автоматически.

## Правила безопасности (живой vault, общий с Obsidian/Syncthing)

- Никогда не правь `.canvas` вручную между вызовами CLI — CLI сам делает
  read→mutate→atomic write + verify-after-write с повторами (гонка с Obsidian/
  Syncthing митигирована, как в расширении §7 ТЗ).
- `~syncthing~*` рядом с целью = синхронизация идёт → CLI вернёт code 5, не пиши в этот момент.
- Удаление/перезапись файлов vault — только с явного согласия пользователя
  (AGENTS.md проекта). `create`/`--new` при коллизии имени отказываются (code 3),
  не перезаписывают.
- Не клади картинки в `.obsidian/`, `__hermes__/` — только `--folder` (дефолт
  `Canvas Inbox`) или рядом с холстом по запросу.

## Синхронность с расширением

Константы раскладки (ROW_WIDTH/GAP/TARGET_HEIGHT/FALLBACK), алгоритм find_free_spot,
формат имени `clip--ГГГГММДД-ЧЧММСС--<hash6>.<ext>` и формат ноды должны совпадать
с ядром Chrome-расширения (core.js проекта obs-canvas-clipper). При изменении
любого из ядер — править оба; в проекте есть тест skill_sync.test.js, сверяющий
Python- и JS-функции на одинаковых входах.

## Related

- `obsidian-vault-automation` — факты Local REST API и формата .canvas.
- `obsidian` — чтение/поиск по vault.
