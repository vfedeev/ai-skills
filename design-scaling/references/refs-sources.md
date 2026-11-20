# Источники референсов и инструменты поиска

Справка для слоя захвата базы фрэнки (`frankie-base.md`): какие API дизайнерских
платформ живы, какие мертвы, чем собирать и чем индексировать. Факты проверены
исследованием с перепроверкой лимитов по официальным документациям; лимиты
периодически меняются — перед интеграцией сверять с источниками в конце файла.

## TL;DR

Открытые API дизайнерских платформ закрываются: Behance-портал мёртв, Pexels
приостановил выдачу ключей, Bing Visual Search API снят с продажи, Pinterest —
только через ручное ревью. Платформы отдают доступ через MCP, но за подписку
(Refero — до 8000 вызовов/мес на Pro, Mobbin — Team/Enterprise). Бесплатный
рабочий стек собирается так: **Are.na (публичные каналы читаются без ключа, есть
официальные MCP/CLI/SDK) → Unsplash / Openverse / Wikimedia Commons (бесплатные
API) → локальный CLIP/SigLIP-индекс своей библиотеки (clip-retrieval / Immich /
LanceDB) + gallery-dl для сбора.**

## 1. Бесплатные API стоков и CC-индексов

| Сервис | Контент | Ключ | Лимиты |
|---|---|---|---|
| Unsplash | фото + иллюстрации | dev-приложение | demo 50/ч, production 1000/ч |
| Pexels | фото+видео | **выдача ключей приостановлена** | 200/ч для старых ключей |
| Pixabay | фото, иллюстрации, **векторы** | бесплатный | 100 req/60с; fullHD/vector после апрува; кэш 24ч обязателен; ToS косит автоматизацию |
| Openverse | CC-агрегатор (Flickr/Wikimedia/StockSnap) | **без ключа** | анонимно 20/мин, 200/день; эндпоинт бывает 504 |
| Wikimedia Commons | свободный арт/SVG | ключа нет, нужен честный User-Agent | аноним 10/мин, UA-compliant 200/мин |
| Flickr | CC-фото | non-commercial ключ бесплатен | 3600/ч |

## 2. Дизайнерские платформы

- **Are.na** — лучший легальный вход: чтение публичных каналов без токена (~30 reads/мин), официальные MCP + CLI + SDK.
- **Dribbble** — API v2, self-service регистрация, OAuth, 60/мин и 1440/сут; ToS: «scraping strictly prohibited».
- **Behance** — портал ключей 404, новые не выдаются; рабочий путь — gallery-dl (collections/galleries/profiles без авторизации).
- **Pinterest** — API v5 только бизнес-аккаунт + ручное ревью (Trial 1000/сут); gallery-dl работает через cookies.
- **Refero / Mobbin** — официальные MCP есть, но только в платных тарифах.
- **Designspiration / Godly / UI Garage / Land-book / Savee** — API нет; только HTML, у части robots с AI-ограничениями (Land-book наоборот явно разрешает AI-краулеры).

## 3. MCP-серверы (community)

В официальном каталоге MCP дизайн-серверов нет. Живое в community: **Awwwards MCP**
(без ключа: поиск сайтов по цветам/тегам, design DNA), **Unsplash MCP**,
**Refero Skill/MCP** (платный), **asset-finder** (иконки/логотипы/векторы без
ключей, `npx`), Pinterest MCP unofficial (ToS-риск). Тренд: ниша уходит в
«skill + hosted-MCP», лидеры живут <1 года — ожидать churn.

## 4. Локальная семантика (своя библиотека, бесплатно, без квот)

- **clip-retrieval** (MIT) — text→image / image→image по локальному корпусу, CLI.
- **Immich** — self-hosted хранилище: SigLIP2-поиск (RU поддерживается), REST+CLI, ~6 мс/запрос на CPU. Форк **open-noodle/gallery** добавляет автоклассификацию картинок.
- **LanceDB** — embedded векторная БД (файл в папке, без сервера); **FAISS/Qdrant** — классика.
- **gallery-dl** (⚠ переехал на Codeberg) — сбор: Behance ✔ Pinterest ✔ Flickr ✔ Are.na ✔ ArtStation ✔; Dribbble ✖ Designspiration ✖ Savee ✖.
- **CocoIndex** — инкрементальный ETL «папка → CLIP-эмбеддинги → индекс».
- Готового репо «scrape→embed→search» одной связкой нет — собирается из кубиков за вечер.
- Стоимость индексации: vision-тегирование ~2–6 сек и ~1k токенов на картинку, только для НОВЫХ файлов (догоняющее, не переиндексация); CLIP-эмбеддинги — секунды на пачку, CPU. Поисковый запрос после индексации — миллисекунды.

## 5. Обратный поиск по изображению

Bing Visual Search мёртв (lifecycle-анонс). TinEye — только платно (от $200/5000).
SauceNAO — бесплатный ключ, но тематика иллюстрации/арт, лимиты ~99/сут.
Google Lens — официального API нет (скрейперы хрупкие). Для «найди похожее»
внутри своей базы оптимален локальный clip-retrieval.

## 6. Raindrop как слой захвата (опционально)

- Raindrop хранит **ссылки, не файлы**: у элемента есть URL источника и cover (хотлинка, может протухнуть). Канон картинок остаётся в `Refs/` — Raindrop подходит только как **вход**: захват с телефона/браузера, коллекции = тематики.
- **Официальный REST API** (`api.raindrop.io/v1`): в Settings → Integrations регистрируешь приложение и копируешь **Test token** — для своего аккаунта не нужен полный OAuth-цикл; test-токен, в отличие от обычных (истекают за 14 дней), не сгорает.
- Лимиты: ~120 req/мин (community-данные, требует проверки). ToS разрешает личные интеграции, запрещает клонировать сервис и требователен к вежливости нагрузки.
- Путь без API: **Settings → Export → JSON** — разовая выгрузка всей коллекции, для стартового импорта токен не нужен.
- Схема: `Raindrop-коллекция → синк (cron) → по каждой ссылке gallery-dl/og:image → файл в Refs/ + тегирование → индекс`. Токен — только в `.env` (`RAINDROP_TEST_TOKEN`).

## Уверенность и пробелы

High: Pexels-pause (цитата со страницы), лимиты Unsplash/Dribbble/Pixabay, Bing
retirement, Refero/Mobbin paywall, поддержка сайтов в gallery-dl. Medium:
Openverse «20/мин» (эмпирика, зонд ловил 504), Are.na guest-лимит «30 reads/мин».
Low/гэпы: точные лимиты SauceNAO (за логином), дата закрытия выдачи ключей
Behance, Pinterest MCP (анонсирован, не запущен — следить).

## Источники

[Unsplash docs](https://unsplash.com/documentation) · [Pexels API](https://www.pexels.com/api/) · [Pixabay docs](https://pixabay.com/api/docs/) · [Openverse](https://docs.openverse.org/api/reference/authentication_and_throttling.html) · [Wikimedia rate limits](https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits) · [Dribbble v2](https://developer.dribbble.com/v2/) и [terms](https://developer.dribbble.com/terms/) · [Are.na developers](https://www.are.na/developers/resources) · [Pinterest access tiers](https://developers.pinterest.com/docs/key-concepts/access-tiers/) · [Refero MCP docs](https://doc.refero.design/mcp/getting-started.md) · [Mobbin API](https://docs.mobbin.com/api/quickstart) · [Bing retirement](https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement) · GitHub: [clip-retrieval](https://github.com/rom1504/clip-retrieval) · [Immich](https://github.com/immich-app/immich) · [gallery-dl](https://github.com/mikf/gallery-dl) · [Awwwards-mcp](https://github.com/INSANE0777/Awwwards-mcp) · [unsplash-mcp](https://github.com/hellokaton/unsplash-mcp-server) · [refero_skill](https://github.com/referodesign/refero_skill) · [asset-finder](https://github.com/Erfangit23/asset-finder-mcp)
