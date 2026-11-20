# Среда исполнения: Hermes Agent + figma-console-cloud

Когда скилл исполняет Hermes Agent (а не Claude Code), Figma доступна через MCP
`figma-console-cloud` (плагин Desktop Bridge в Figma Desktop). Скилл `figma-use` —
обязательная прембула и здесь: это самостоятельный донор процедур Plugin API,
загружать его перед первым `figma_execute`.

## Маппинг инструментов

| Claude Code | Hermes |
|---|---|
| `use_figma` | `figma_execute` (тот же Plugin API, параметр `timeout` до 300000 мс) |
| `get_screenshot` | `figma_capture_screenshot` (жёсткий cap: длинная сторона ≤1568 px; страница целиком выходит в масштабе ~0.16 — ритм виден, детали нет; секции снимать отдельно в 0.8) |
| `get_metadata` | read-only скрипт через `figma_execute` (return структуры JSON-ом) |
| `sips` (нарезка фрагментов) | Python + PIL |

## Подключение и его нестабильность

- Перед стартом: `figma_list_open_files`. Ответ «No files connected» / «No plugin connected to cloud relay» → `figma_pair_plugin`, передать дизайнеру 6-символьный код (MCP Bridge → Cloud Mode → Connect); код живёт 5 минут.
- Relay отваливается после ~40 минут простоя — на долгую задачу закладывать перепейринг и не считать отвал ошибкой скрипта.
- Структуру файла без плагина читает REST: `figma_get_file_data` (fileKey из URL `figma.com/design/<fileKey>/...`).

## QA в среде Hermes

- Программная геометрия: `scripts/qa-geometry.js` через `figma_execute` — первичный слой проверки.
- Vision-сверка скриншотов — вторичный слой: параллельные пачки vision-вызовов деградируют (таймауты); после 2 таймаутов менять вход (thumbnail-копия ≤1000px через PIL, короче вопрос), а не долбить повтор.
