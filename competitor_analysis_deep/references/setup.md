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

## Polza.ai

- **Endpoint:** `https://polza.ai/api/v1`
- **Ключ:** `POLZA_API_KEY` в `.env`
- **Формат:** OpenAI-compatible API
- **Вызов:** `delegate_task(model={"provider":"polza.ai","model":"..."})`

## Xiaomi (mimo-2.5)

- **Endpoint:** `https://token-plan-sgp.xiaomimimo.com/v1`
- **Ключ:** `XIAOMI_API_KEY` в `.env`
- **Вызов:** `delegate_task(model={"provider":"xiaomi","model":"mimo-2.5"})`

## Обновление Chromium

При обновлении Playwright версия Chromium может измениться. Проверить:

```bash
ls /home/vvv/.cache/ms-playwright/chromium-*/chrome-linux64/chrome
```

Если путь измён — обновить в SKILL.md и в context Фотографа.
