# Справочник: именование БЭМ

Источники (проверены 2026-09-24): ru.bem.info/methodology/naming-convention, bem.info/en/methodology/history, getbem.com/naming, yoksel.github.io/easy-markup/bem-rules, habr.com/ru/articles/684170, css-tricks.com/bem-101.

## Сущности

- **Блок** — независимый компонент, значим сам по себе (`menu`, `search-form`). Имя блока = неймспейс для его элементов и модификаторов.
- **Элемент** — часть блока, вне блока бессмысленна (`menu__item`). Одинаковые элементы одного блока имеют одно имя (все пункты меню — `menu__item`).
- **Модификатор** — свойство блока/элемента: вид, состояние, поведение. Типы: булевый (`menu_hidden` — значение в имя не входит) и ключ-значение (`menu_theme_islands`). У сущности может быть несколько модификаторов одновременно.

Тест «блок или элемент» (bem.info/quick-start): можно ли отделить от родителя и перенести, сохранив смысл → блок; нельзя → элемент.

## Классическая схема (bem.info)

`блок-имя__элемент-имя_имя-модификатора_значение`

1. Только строчные латинские буквы и цифры; слова внутри имени разделяются дефисом `-` (`search-form__submit-btn`).
2. Элемент отделяется двойным подчёркиванием `__`.
3. Имя модификатора — одинарным `_`; значение модификатора — ещё одним `_` (в имени максимум два `_`-разделителя).
4. **Элементов элемента нет**: ❌ `news__item__title` (bem.info/naming-convention). Решение (yoksel): объявить вложенный блок `news-item` → `news-item__title`; на DOM-узле допустим микс `class="news__item news-item"`. При этом DOM-вложенность элементов друг в друга разрешена (bem.info/html «Nesting of elements») — запрещён именно такой синтаксис имени.
5. Префиксы `b-`, `c-`, `g-`, `h-`, `l-` — архаика 2006–2008 (bem.info/history): «We originally used prefixes but eventually dropped them». В современной схеме не используются.
6. Класс модификатора в HTML идёт только в паре с базовым: `class="menu menu_theme_islands"`, не один (bem.info/faq «Why not write block_mod instead of block block_mod»: иначе дублирование базовых стилей).
7. Модификатор элемента сохраняет и блок, и элемент: `menu__item_visible`.
8. Имя селектора должно полностью и точно описывать БЭМ-сущность (bem.info/css «Naming»). Имена `icon`, `text`, `theme_islands` без имени блока — неинформативны.

## Two-dashes (getbem.com, «западная»)

`block__elem--mod` / `block__elem--mod-val` / `block--mod`:
- `__` для элемента сохраняется;
- модификатор через `--`, ровно один;
- слова/значение внутри модификатора — через дефис (`block__elem--color-red`);
- базовый класс блока остаётся в разметке: `<div class="block block--mod">`, один `block--mod` — ошибка (getbem «Bad»).

⚠️ На bem.info «Two Dashes» описана **иначе**: `block-name__elem-name--mod-name_mod-val` (модификатор через `--`, значение через `_`). Обе схемы называются одинаково — при обсуждении уточнять, какая из двух имеется в виду. В проекте — одна схема; смешивание `_` и `--` в одном файле = самая частая ошибка.

Прочие альтернативы bem.info: CamelCase (`blockName__elemName_modName_modVal`), React (`BlockName-ElemName_modName_modVal`, используется в bem-react), No Namespace (`_available` — не рекомендуется: ломает миксы, нельзя определить владельца модификатора). Поддержка произвольной схемы машинно: `@bem/sdk.naming` / пакет `bem-naming`.

## Стиль имён: семантика, не визуал

### Секция — корень имени, не страница

Префикс каждого имени — название **секции** дизайна (области страницы: `hero`, `about`, `booking`, `contacts`), не имя артборда/страницы. Секция = БЛОК. ❌ `main-page__title` — блок не может быть страницей; ✅ `hero__image`. Историческая справка: в первой ревизии правил была дефисная форма `<секция>-<элемент>` (`hero-heading-h2`), она отвергнута пользователем — машина не отличает границу блока от элемента; в валидаторе она остаётся легальной схемой bem.info, но в проектах пользователя не применять.

Если секций в Figma нет — имена секций определять по содержимому (скриншоты областей) и согласовать с пользователем до применения.

**Дефолт проекта — классика**: секция = блок, элемент через `__` (`hero__image`, `booking__heading-h2`, `footer__logo-text`). Слова внутри имени — дефисом; `__` в имени ровно один.

### Одинаковые элементы с разной геометрией — модификатор

Правило bem.info: все одинаковые элементы блока носят одно имя. Значит после построения плана ОБЯЗАТЕЛЬНА проверка конфликтов: сгруппировать узлы по имени и сравнить геометрию (`w/h`: >1.35 `horz`, <0.74 `vert`, иначе `sq`). Одно имя + разный ratio = модификатор: `relevant__card-image_horz`, `relevant__card-image_vert` (ключ-значение, `_` перед именем модификатора, `__` ровно один — валидатор это пропускает). Не решать «на глаз по картинке» — только по фактическим w/h из дерева.

Мелкие внутренние листья векторной графики (буквы-векторы логотипа, части boolean-иконок) — это НЕ одноимённые элементы-контейнеры, суффикс роли: `footer__logo-text-decor`, `footer__socials-icon-decor`; сам container-слой остаётся с чистым именем (`footer__logo-text`).

### Части одного элемента — wrapper-фрейм

Одно имя элемента у нескольких слоёв допустимо, только если это независимые экземпляры (три карточки → три `relevant__card`). Если слои — **части одного целого** (предложение, разрезанное на две строки ради контроля переноса), их надо собрать в wrapper-фрейм с именем `<блок>__<элемент>-wrap`: внутри слои остаются `relevant__heading-h2`, снаружи — `relevant__heading-h2-wrap`. Суффикс `-wrap` — описательный часть имени элемента (приём из практики yoksel), синтаксис классики не нарушает: `__` один, элемента-элемента нет.

⚠️ Отступление (проговаривать пользователю): wrapper — служебный слой дизайна, в HTML он обычно не переносится (разрезанный заголовок станет одним `<h2>`), CSS-судьбы у `-wrap` может не быть.

Не путать с группировкой экземпляров: три пары image+heading+text в галерее — это три элемента-блока `relevant__card` (обернуть содержимое каждой карточки), а не один wrapper.

### Инстансы компонентов — самостоятельные блоки, без секционного префикса

Тест «можно отделить от родителя и перенести, сохранив смысл → блок» (bem.info/quick-start) прямо отвечает на вопрос про общие кнопки/карточки: компонент, кочующий между секциями, — БЛОК. Имя слоя-инстанса = имя блока (обычно имя его компонент-сета): `logo`, `button`, `product-card` — НЕ `hero__navigation-logo` и не `booking__form` для инстанса сета `book now`. Внутри таких блоков элементы названы от его же имени: `logo__icon`, `button__text`.

«Кнопка в хиро» ≠ переименование кнопки: связь выражают миксом в разметке (`class="button hero__button"`) — geometry/позиционирование задаёт родитель, внешний вид остаётся блоку (bem.info/css «External geometry»). Двойного имени у слоя нет; `hero__button` появляется в HTML как второй класс, а не как новое имя компонента.

Исключение: «кнопка», которая не является компонентом и существует только в одной секции, — честный элемент `hero__button`.

В Figma-аудите: перед переименованием проверять `node.type==="INSTANCE"` и читать `mainComponent.parent.name` (сет) → транслит lowercase-hyphen. Не трогать имена вариант-свойств (`Color=biege`, `size=large`) — контракт Figma.

Как искать: группировка одноимённых слоёв, затем проверка связности — расстояние/перенос строки/один ли это текст по смыслу (читать `characters`); решение — в таблицу корректур с пометкой «wrapper».

### Текст: имя по текстовому стилю, а не по угаданной роли

Если в файле заданы текстовые стили (в примерах: `H1`, `H2`, `H3`, `text`, `Descripter`, `Big text`, `Menu`, `Buttons`, часто с префиксом брейкпоинта `1920-1000px/H2` — берётся последняя часть после `/`), имя элемента = имя стиля. НЕ лепить `__title`/`__text` на глаз — без привязки к стилю это мусор, различающий H2 и обычный абзац только по высоте шрифта в голове аудитора.

Схема: стили H1–H6 → `heading-hN`, остальные — транслит lowercase-hyphen от имени стиля: `Descripter` → `descripter`, `Big text` → `big-text`, `text` → `text`, `Menu` → `menu`, `Buttons` → `buttons`. С блоком-секцией: `about__heading-h2`, `about__descripter`, `hero__big-text`. Один блок с двумя разными стилями → разные имена, а не два `__title`.

Как читать: в дампе дерева для text-узлов брать `node.textStyleId` → `getLocalTextStylesAsync()` / `getStyleByIdAsync(id).name`. Если стиль не назначен — смотреть `characters`/размер шрифта и честно помечать в таблице как low-confidence.

### img vs decor

Фрейм/фигура с image-заполнением (растровая картинка, фото) → `блок__image` (`hero__image`, `card__image`), НЕ `decor`. `decor` — только векторная/текстовая графика: векторы, boolean-операции, текстуры, маски, подложки-фигуры. Как читать: `node.fills.some(f => f.type === 'IMAGE')` для фреймов и прямоугольников.

✅ `button_disabled`, `notice_type_error`, `card__price_old` ❌ `button_grey`, `red-text`, `frame-1-copy`. Имя отражает роль в UI, а не CSS-свойство (bem.info/faq «How to choose a name for a modifier»). Размер/тема как вариативность — тоже семантика варианта, а не конкретное свойство: `button_size_l`, `menu_theme_islands`.

## Шаблоны: типовые элементы макета

Классическая схема; для two-dashes модификатор заменять на `--`.

### Хедер / футер / навигация
`page-header`, `page-header__logo`, `logo`, `logo__image`, `logo__caption`, `page-nav`, `page-nav__list`, `page-nav__item`, `page-nav__item_current`, `page-nav__link`, `site-search`, `site-search__field`, `site-search__button`, `burger`, `burger__line`, `burger_opened`, `page-footer`, `page-footer__contacts`, `social-links`, `social-links__link_type_vk`, `breadcrumbs`, `breadcrumbs__item`, `breadcrumbs__item_current`, `breadcrumbs__link`, `breadcrumbs__separator`

Микс для позиционирования независимого блока в хедере: `class="page-nav page-header__nav"` (bem.info/css «External geometry and positioning»).

### Кнопка
`button`, `button_size_s/m/l`, `button_theme_primary`, `button_type_submit`, `button_disabled`, `button_pressed`, `button_focused`, `button_hovered`, `button_loading`, `button__text`, `button__icon`

### Карточка (услуга/товар/новость)
`card`, `card__image-link`, `card__image`, `card__body`, `card__title`, `card__text`, `card__price`, `card__price_old`, `card__price_new`, `card__features`, `card__feature`, `card__button`, `card_theme_service`, `card-list`, `card-list__item`, `badge`, `badge_status_new`, `badge_status_sale`. Сложный внутренний слой — отдельный блок: `card-meta`, `card-meta__date` (не `card__meta__date`).

### Форма
`form`, `form__row`, `form__label`, `form__input`, `form__control`, `form__submit`, `form__error`, `form__error_visible`, `form_theme_dark`; контролы-блоки: `text-input` (+`_invalid`, `_focused`, `_filled`), `textarea`, `number-input`, `checkbox`, `checkbox__input`, `checkbox__box`, `checkbox__label`, `radio`, `radio_checked`, `select`, `select__toggle`, `select__options`, `select__options_opened`, `select__option`, `select__option_checked`

Поля формы — самостоятельные блоки, элемент формы даёт им микс: `class="text-input form__input"`.

### Hero / промо / слайдер
`hero`, `hero__bg-image`, `hero__content`, `hero__title`, `hero__subtitle`, `hero__actions`, `hero__button`, `hero__link`, `hero__badge`, `hero_theme_dark`; `slider`, `slider__track`, `slider__slide`, `slider__slide_active`, `slider__arrow`, `slider__arrow_prev`, `slider__arrow_next`, `slider__dots`, `slider__dot`, `slider__dot_current`

### Прочее
`section`, `section__container`, `section__header`, `section__body`, `section_theme_alt`; `section-title`, `section-title__text`, `section-title__accent`; `accordion`, `accordion__item`, `accordion__item_opened`, `accordion__header`, `accordion__title`, `accordion__icon`, `accordion__panel`; `tabs`, `tabs__list`, `tabs__tab`, `tabs__tab_active`, `tabs__panel`, `tabs__panel_visible`; `popup`, `popup_opened`, `popup__overlay`, `popup__container`, `popup__title`, `popup__close`; `notice`, `notice_status_success`, `notice_status_error`, `notice__icon`, `notice__text`; `pagination`, `pagination__page`, `pagination__page_current`, `pagination__arrow`, `pagination__arrow_next`; `scroll-top`, `scroll-top_visible`; `grid`, `grid__col`, `container`, `row`, `col`, `col_size_6`; `icon`, `icon_size_m`, `icon_type_check`; `avatar`, `avatar_size_s`; `tag`, `time`

## CSS-принципы, связанные с именованием (bem.info/methodology/css)

- Селекторы: только классы, без `#id` и без тегов. Не комбинировать `button.button` и `.button.button_theme_islands` — растёт специфичность, модификатор перестаёт переопределять.
- Вложенные селекторы минимизировать; допустимое исключение — «состояние блока → стиль элемента»: `.form_invalid .form__input`.
- Внешнюю геометрию (`margin`, `position`) задаёт родитель через микс (`header__search-form`), сам блок её не задаёт → переиспользуемость.
- Микс ≠ модификатор (bem.info/faq): модификатор — повторяемый вариант блока; микс — одноразовая привязка к конкретному контексту.
- Итоговая специфичность плоская и низкая; всё — одиночные классы.

## Формальная проверка имени (habr 684170)

Разрешены только `[a-z_-]`; `_`-разделитель не может стоять раньше `__`; не более двух `_` (классика); `_{3,}` запрещено; имя не начинается и не заканчивается разделителем; дефис не соседствует с подчёркиванием (`-_`, `_-`, `--` в классике). Реализовано в `scripts/validate_bem_name.py` (обе схемы, JSON-вывод, флаг `--figma` для авто-имён).

## Частые антипаттерны (сводка)

```
❌ b-menu                          — префикс-архаика
❌ <li class="item">                — элемент без имени блока (теряется неймспейс)
❌ news__item__title                — элемент элемента
❌ <button class="button_disabled">   — модификатор без базового класса
❌ block__red-text                  — визуальное имя вместо семантического
❌ .card .card__title { }            — вложенный селектор, специфичность ↑
❌ div.card__image { }               — селектор с тегом
❌ CamelCase / Menu__Item            — верхний регистр не допускается
❌ смешение схем: .menu__item--visible в classic-проекте
```
