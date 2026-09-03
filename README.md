# AI Skills

Набор скиллов для Hermes Agent, Codex или Claude Code.

## Скиллы

| Скилл | Что делает | Требования |
|-------|-----------|------------|
| [ai-transcribe](ai-transcribe/) | Транскрибация аудио/видео интервью и созвонов. Разбивает по паузам, распознаёт речь через Groq/OpenAI, разделяет по спикерам. Результат — MD-файл с тезисами. | Python 3.8+, API-ключ Groq или OpenAI |
| [adv-checkup](adv-checkup/) | Проверка рекламных макетов на соответствие законодательству РФ (38-ФЗ, 436-ФЗ, 53-ФЗ). Анализирует макет, сверяет с нормами, выдаёт сводку нарушений. | Модель с vision |
| [ultraui-layers](ultraui-layers/) | Визуальный анализ сайтов по 6 слоям Ultra UI (типографика, цвет, анимации, сетка, графика, медиа) | Модель с vision |
| [competitor_analysis_deep](competitor_analysis_deep/) | Глубокий конкурентный анализ: сбор данных из брифа, скриншоты в 3 вьюпортах, таблица по шаблону Апрок (35 вопросов), факт-чек. Multi-agent: Директор, Веб-парсеры, Фотограф, Критик. | Playwright + Chromium, SearXNG (опц.), провайдер LLM |

## Установка

### Через git

```bash
git clone https://github.com/vfedeev/ai-skills.git
cp -r ai-skills/<название-скилла> ~/.hermes/skills/
```

### Через ZIP

Скачать архив со страницы [Releases](https://github.com/vfedeev/ai-skills/releases), распаковать и скопировать нужную папку в `~/.hermes/skills/`.

### Пути установки

| Агент | Путь |
|-------|------|
| Hermes Agent | `~/.hermes/skills/` |
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.codex/skills/` |

## Требования

Зависят от конкретного скилла — смотрите README в подпапке каждого скилла.

## Лицензия

MIT
