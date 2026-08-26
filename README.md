# AI Skills

AI Skills for Hermes Agent.

## Skills

### ai-transcribe
Транскрибация аудио и видео интервью/созвонов. Поддерживает Groq API (Whisper), OpenAI API и другие STT-провайдеры.

**Установка:**
```bash
# Клонировать скилл
git clone https://github.com/vfedeev/ai-skills.git
cp -r ai-skills/ai-transcribe ~/.hermes/skills/media/

# Запустить предконфигурацию
python3 ~/.hermes/skills/media/ai-transcribe/scripts/setup.py
```

**Требования:**
- Python 3.8+
- ffmpeg (для видео)
- API-ключ Groq или OpenAI
