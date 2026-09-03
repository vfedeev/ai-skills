# Setup — Зависимости для скриншотов

## Playwright (Python)

- **Venv:** `/home/vvv/.venvs/playwright/`
- **Python:** `/home/vvv/.venvs/playwright/bin/python3`
- **Версия:** 1.62.0
- **Установка:** `uv venv /home/vvv/.venvs/playwright && source /home/vvv/.venvs/playwright/bin/activate && uv pip install playwright`

## Chromium (headless)

- **Бинарник:** `/home/vvv/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome`
- **Версия:** Google Chrome for Testing 151.0.7922.34
- **Установка:** `source /home/vvv/.venvs/playwright/bin/activate && playwright install chromium`
- **Системные зависимости:** `playwright install chromium --with-deps` (требует sudo)

## SearXNG

- **Endpoint:** `http://localhost:8888/search`
- **Формат:** POST, `q={query}&format=json`
- **Движки:** Яндекс (лучший для Runet), Google CSE, Bing, Qwant
- **Документация:** скилл `searxng-setup`

## Провайдеры

Модели для субагентов выбираются через `clarify` при запуске. Провайдер должен быть настроен в Hermes (`config.yaml` + ключ в `.env`).

Примеры провайдеров:
- **Polza.ai** — OpenAI-compatible, `https://polza.ai/api/v1`, ключ `POLZA_API_KEY`
- **Xiaomi** — `https://token-plan-sgp.xiaomimimo.com/v1`, ключ `XIAOMI_API_KEY`
- **Alltokens** — бесплатные модели, `https://api.alltokens.ai/v1`
- **Текущая модель сессии** — без дополнительной настройки

## Обновление Chromium

При обновлении Playwright версия Chromium может измениться. Проверить:

```bash
ls /home/vvv/.cache/ms-playwright/chromium-*/chrome-linux64/chrome
```

Если путь изменился — обновить в SKILL.md и в context Фотографа.
