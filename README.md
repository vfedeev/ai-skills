# AI Skills

AI Skills for Hermes Agent — набор скиллов для расширения возможностей агента.

## Доступные скиллы

| Скилл | Описание |
|-------|----------|
| [ai-transcribe](ai-transcribe/) | Транскрибация аудио и видео интервью/созвонов через Groq/OpenAI |

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

- Hermes Agent
- Python 3.8+
- Зависят от конкретного скилла (см. README в подпапке)

## Лицензия

MIT
