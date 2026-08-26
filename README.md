# AI Skills

AI Skills for Hermes Agent, Codex или Claude Code — набор скиллов для расширения возможностей агента.

## Доступные скиллы

| Скилл | Описание |
|-------|----------|
| [ai-transcribe](ai-transcribe/) | Транскрибация аудио и видео интервью/созвонов через Groq/OpenAI |

### ai-transcribe

Расшифровывает аудио и видео записи разговоров, интервью, созвонов. Разбивает длинные записи по паузам, распознаёт речь через Groq или OpenAI API, разделяет по спикерам, очищает от ошибок. Результат — отформатированный MD-файл с тезисами и ТЗ.

## Установка

```bash
# Клонировать репозиторий
git clone https://github.com/vfedeev/ai-skills.git

# Скопировать нужный скилл
cp -r ai-skills/<skill-name> ~/.hermes/skills/media/

# Запустить предконфигурацию (если есть setup.py)
python3 ~/.hermes/skills/media/<skill-name>/scripts/setup.py
```

## Требования

- Python 3.8+
- Зависят от конкретного скилла (см. README в подпапке)

## Лицензия

MIT
