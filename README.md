# AI Skills

AI Skills for Hermes Agent, Codex или Claude Code — набор скиллов для расширения возможностей агента.

## Доступные скиллы

| Скилл | Описание |
|-------|----------|
| [ai-transcribe](ai-transcribe/) | Транскрибация аудио и видео интервью/созвонов через Groq/OpenAI |

### ai-transcribe

Расшифровывает аудио и видео записи разговоров, интервью, созвонов. Разбивает длинные записи по паузам, распознаёт речь через Groq или OpenAI API, разделяет по спикерам, очищает от ошибок. Результат — отформатированный MD-файл с тезисами и ТЗ.

## Установка

### 1. Скачать скилл

**Через git:**
```bash
git clone https://github.com/vfedeev/ai-skills.git
cp -r ai-skills/<skill-name> <install-path>
```

**Через zip:**
Скачать архив со страницы [Releases](https://github.com/vfedeev/ai-skills/releases) и распаковать в `<install-path>`.

### 2. Указать путь установки

| Агент | Путь установки |
|-------|----------------|
| Hermes Agent | `~/.hermes/skills/media/` |
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.codex/skills/` |

### 3. Запустить предконфигурацию

```bash
python3 <install-path>/<skill-name>/scripts/setup.py
```

Скрипт проверит зависимости и настроит API-ключи.

## Требования

- Python 3.8+
- Зависят от конкретного скилла (см. README в подпапке)

## Лицензия

MIT
