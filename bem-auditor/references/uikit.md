# Справочник: UIkit 3 — классы и состояния

Источники (извлечено 2026-09-24 с getuikit.com/docs/*): button, card, form, alert, modal, nav, tab, accordion, badge, animation. Это **подмножество** компонентов UIkit. Для компонента вне списка — сказать, что справочник его не покрывает, и дать ссылку `getuikit.com/docs/<component>`; не выдумывать классы.

## Конвенция UIkit

Классы `uk-<компонент>`; модификаторы через дефис (`uk-button-primary`); глобальные состояния `uk-active`, `uk-disabled`, `uk-open`. JS-компоненты инициализируются атрибутами `uk-*` (`uk-dropdown`, `uk-toggle`, `uk-accordion`). Отключённое состояние контролов — HTML-атрибут `disabled`, не класс.

## Button (docs/button)

`uk-button` + стиль: `uk-button-default`, `-primary`, `-secondary`, `-danger`, `-text`, `-link`. Размер: `uk-button-small`, `uk-button-large`. Группа: `uk-button-group`. На всю ширину: `uk-width-1-1` (компонент Width). Отступы между кнопками в стеке — атрибут `uk-margin` на родителе.

## Card (docs/card)

`uk-card` + `uk-card-body`; заголовок `uk-card-title`. Стиль (обязателен, по умолчанию карточка пустая): `uk-card-default`, `-primary`, `-secondary`, `-overlay`. Размер падинга: `uk-card-small`, `-large`. Ховер: `uk-card-hover`. Медиа: `uk-card-media-top`, `-bottom`, `-left`, `-right` (+ `uk-cover-container`, атрибут `uk-cover`). Бейдж: `uk-card-badge` (обычно вместе с `uk-label`).

## Form (docs/form)

Контролы: `uk-input`, `uk-select`, `uk-textarea`, `uk-radio`, `uk-checkbox`, `uk-range`; `uk-fieldset`, `uk-legend`. Состояния валидации: `uk-form-danger`, `uk-form-success`. Размеры: `uk-form-small`, `uk-form-large`. Ширина: `uk-form-width-small`, `-medium`, `-large`, `uk-form-controls`.

## Alert (docs/alert)

Атрибут `uk-alert` на блочном элементе. Стиль: `uk-alert-primary`, `-success`, `-warning`, `-danger`. Закрытие: `uk-alert-close` (+ атрибут `uk-close`).

## Modal (docs/modal)

Контейнер: атрибут `uk-modal` + `id` (на `<div>`). Внутри: `uk-modal-dialog`, `uk-modal-body`, `uk-modal-title`. Закрытие: `uk-modal-close`, `uk-modal-close-default`, `uk-modal-close-outside`; полный экран `uk-modal-full`. Тoggler: `uk-toggle="target: #id"`.

## Nav (docs/nav)

`uk-nav` — класс на `<ul>` (для аккордеон-поведения — атрибут `uk-nav`, он сам добавляет класс). Стиль-модификатор: `uk-nav-default`, `-primary`, `-secondary`. Активный пункт: `uk-active` на `<li>`. Родитель подменю: `uk-parent`; подменю `uk-nav-sub`. Разделитель `uk-nav-divider`, заголовок группы `uk-nav-header`, подзаголовок `uk-nav-subtitle`, иконка `uk-nav-parent-icon` (на `<span>`). Смежные навигации — отдельные компоненты со своими классами: `uk-navbar-nav`, `uk-dropdown-nav`, `uk-subnav`, `uk-tab`, `uk-iconnav`, `uk-dotnav`, `uk-thumbnav`, `uk-slidenav` — сверяться с их страницами.

## Tab (docs/tab)

Атрибут `uk-tab` на `<ul>`, пункты — `<a>` внутри `<li>`. Состояния: `uk-active`, `uk-disabled` (у disabled-пункта убрать `href`). Позиция: `uk-tab-bottom`, `uk-tab-left`, `uk-tab-right`. Контент — `uk-switcher`.

## Accordion (docs/accordion)

Атрибут `uk-accordion` на `<ul>`. Стиль: `uk-accordion-default`. `uk-accordion-title` (на `<a>`), `uk-accordion-content`, иконка — атрибут `uk-accordion-icon` на `<span>`. Открытый пункт: класс **`uk-open`** на `<li>` (не `uk-active`).

## Badge / Label

`uk-badge` — только базовый класс, цветовых модификаторов нет. `uk-label` + `uk-label-success`, `-warning`, `-danger`. В карточке — `uk-card-badge`.

## Animation (docs/animation)

`uk-animation-fade`, `-scale-up`, `-scale-down`, `-slide-top`, `-slide-bottom`, `-slide-left`, `-slide-right`, варианты `-small` и `-medium` у slide-*, `-kenburns`, `-shake`, `-stroke`. Выходная (обратная) анимация — `uk-animation-reverse` вместе с основной. Триггер по ховеру/фокусу: родитель с `uk-animation-toggle` + `tabindex="0"`. Появление при скролле — через `uk-scrollspy`.

## Частые ВЫДУМКИ в макетах (флагить как несуществующие)

| В макете | Реальность |
|---|---|
| `uk-button-hover`, `uk-button-focus`, `uk-button-active` | hover/focus — CSS-псевдоклассы, у UIkit таких классов для кнопки нет; именованные состояния только там, где их задаёт JS (`uk-active`, `uk-open`) |
| `uk-card-rounded`, `uk-card-shadow` | не существует; тени — утилиты `uk-box-shadow-*`, радиусы — ручной стиль |
| `uk-open` на кнопке/модалке | `uk-open` — открытый пункт accordion/nav/off-canvas |
| `uk-disabled` на `<input>` | для контролов формы — атрибут `disabled`; `uk-disabled` — для `<li>` в nav/tab |
| `uk-button--primary`, `uk-btn-primary`, `button-uk-primary` | правильно `uk-button-primary`; `btn` без `uk-` — не UIkit (это Bootstrap) |
| `uk-animation-fade-out` | выход = `uk-animation-fade uk-animation-reverse` |
| `uk-form-input`, `uk-input-field` | только `uk-input` |
| `uk-nav-item`, `uk-nav-link` | у nav нет таких классов; пункт — `<li>`/`<a>` внутри `uk-nav`, активный — `uk-active` на `<li>` |

## Варианты компонентов в Figma

Фреймы-варианты компонент-сетов с именами `state=hover`, `size=large`, `text#123:1` — легальный синтаксис Figma, а **не** CSS-классы. Не требовать их переименования ради мнимого соответствия API: класс инстансу даёт базовый `uk-*`. Предлагать правку варианта только если (а) пользователь явно хочет, чтобы все имена слоёв были классами, или (б) имя варианта противоречит реальному API (например, вариант `state=uk-button-hover` — путаница состояния и класса).
