# Figma MCP: снятие дерева и переименование

Инструменты — `mcp__figma_official__*` (в Hermes это deferred tools: при первом обращении загрузить схему через `tool_describe`, вызывать через `tool_call`).

**Перед каждым `use_figma` обязан быть загружен skill `figma-use`** (требование инструмента) и передан `skillNames: "figma-use"`. Полные правила API — там же, в `references/gotchas.md`.

## Извлечение параметров из URL

`https://figma.com/design/<fileKey>/<Name>?node-id=12-345` → `fileKey` — 22–128 alphanumeric, `nodeId` — `12:345` (дефис заменить на двоеточие). Для `branch/<branchKey>` — branchKey как fileKey. Формат nodeId: `\d+:\d+`. Без node-id — спросить ссылку на фрейм или вызвать `get_metadata` без nodeId (вернёт список страниц). Пустой/угаданный nodeId передавать нельзя.

## Dump tree (read-only)

```js
// use_figma: dump layer tree under a node, with types and instance provenance
const root = await figma.getNodeByIdAsync("NODE_ID");
if (!root) return { error: "node not found" };
if (root.type === "PAGE") await figma.setCurrentPageAsync(root);
else if (root.parent && root.parent.type === "PAGE") await figma.setCurrentPageAsync(root.parent);

const out = [];
function walk(n, depth) {
  out.push({
    id: n.id,
    name: n.name,
    type: n.type,
    depth,
    mainComp: n.type === "INSTANCE" && n.mainComponent ? n.mainComponent.name : undefined,
    setName: n.type === "COMPONENT" && n.parent && n.parent.type === "COMPONENT_SET" ? n.parent.name : undefined
  });
  if ("children" in n && depth < 12) for (const c of n.children) walk(c, depth + 1);
}
walk(root, 0);
return { count: out.length, nodes: out };
```

Если `count` велик — писать имена в `names.txt` построчно (только `name`) и гнать через валидатор; `depth`/`mainComp` использовать для контекста спорных узлов.

Быстрый обзор структуры без кода: `get_metadata(fileKey, nodeId)` → XML с id/типом/именем/позицией. `get_design_context` для аудита имён **не** нужен (он для design→code).

## Wrapper-фреймы: техника (проверено живым прогоном на двух разрезанных заголовках)

Обёртка вокруг 2+ sibling-слоёв одного элемента = **ФРЕЙМ** (не GROUP: фрейм не ломает визуал — verified byte-for-byte, и он ближе к DOM-контейнеру; решение пользователя). Группировка `figma.group()` разрешена как организационная операция и naming, но для wrapper выбирается фрейм. Auto-layout — ЗАПРЕЩЁН (SKILL.md правило 4).

1. **Стоп-условие**: если у родителя `layoutMode !== "NONE"` — не оборачивать (auto-layout вставит лишнюю рамку в поток), предложить вручную.
2. Не оборачивать детей `INSTANCE` (реparent внутрь инстанса заблокирован API).
3. Записать `absoluteTransform` всех заворачиваемых слоёв ДО.
4. `figma.createFrame()` → `fills=[]`, `clipsContent=false`, `layoutMode="NONE"` (явно!), `resize(bbox)`, `parent.insertChild(min(индексы), w)`.
5. **Ловушка**: `w.x/y` в Plugin API — ОТНОСИТЕЛЬНЫЕ к родителю. Ставить `bbox - parent.absoluteTransform`, не абсолютные координаты. Иначе обёртка уезжает на координаты родителя (реальный баг первого прогона).
6. `appendChild` каждого слоя (вызывает реparent) → затем слоям выставить `x = absOld - wAbsNew`.
7. **Верификация**: сравнить `absoluteTransform` каждого слоя до/после — обязаны совпасть байт в байт; вернуть числа в результат скрипта. Любое расхождение >0 px — `figma.ungroup`/удалить пустую обёртку НЕ удаляя детей: детей сначала вынуть обратно в родителя, обёртку снести после того, как она пуста (см. правило «не удалять контейнер с детьми»).
8. **Смертельный питфолл (потеря фрейма галереи)**: скрипт упал на последнем шаге после того, как дети уже были перенесены; «чистка сироты» удалила фрейм ВМЕСТЕ с детьми. Правило: перед любым `remove()` читать `node.children.length` и удалять только явно пустые контейнеры; ошибка `node does not exist` на пустой группе — безвредна (Figma удаляет пустые группы сама), ретраить destructive-кодом нельзя.

## Уроки боевого прогона (1612 переименований за сессию)

- **Генератор плана должен ловить ГОЛЫЕ автоимена** (`Vector`, `Rectangle`, `Group` без номера). Валидатор скилла их детектит (`FIGMA_NAME_RE`), но если в плане брать только паттерн `Тип \d+` — одиночные `Vector` проскакивают; добирать отдельным батчем.
- **Иконочные кадры `fluent:*`, `mdi*`, `solar*`, `streamline*`** — имена от плагина иконок (Iconify), по ним плагин пересобирает иконку. НЕ переименовывать, не флагить как ошибку БЭМ.
- **Размер батча**: ~320 id ≈ 11–12 KB кода — надёжно; лимит `use_figma` — 50k символов кода. Один батч = одна страница (смена внутри скрипта).
- **`for (const [id] of Object.keys(MAP))` — баг**: деструктурирует строку (id=первый символ) → ложные "MISSING". Всегда `Object.entries`.
- **Гонки с живым редактором**: между аудит-дампом и применением поддерево могут удалить (проверка: `getNodeByIdAsync` → null, id нет в свежем `get_metadata`). Не ретраить и не искать «где оно» — доложить как not_found/removed.
- **Парсинг XML из `get_metadata`**: теги с дефисом (`rounded-rectangle`) → regex `<([\w-]+)`; глубина = отступ/2.
- **Валидатор на stdin с ~2000 имён зависает** (>300s) — гонять пачками по ≤500 или файлами по макетам.
- **Имя текстового слоя ≠ контент**: rename не трогает текст, но после аудита слой «info@…» перестаёт искаться по содержимому — предупредить пользователя.

## Rename batch (после явного «да» пользователя)

```js
// use_figma: rename layers from a MAP — sets ONLY node.name, no text mutation
const MAP = { "12:345": "card__title", "12:346": "card__text" };
const mutated = [], missing = [], skipped = [];
for (const [id, name] of Object.entries(MAP)) {
  const n = await figma.getNodeByIdAsync(id);
  if (!n) { missing.push(id); continue; }
  if (n.name === name) { skipped.push(id); continue; }
  n.name = name;
  mutated.push(n.id);
}
return { mutatedNodeIds: mutated, missing, skipped, planned: Object.keys(MAP).length };
```

Правила:
- ≤50 пар на вызов; больше — несколько вызовов. Разные страницы → параллельно в одном сообщении; одна страница → последовательно (одна смена страницы на вызов).
- После каждого батча — verification: повторное чтение имён по `mutatedNodeIds` и сверка с планом (отдельный read-only вызов или `getNodeByIdAsync` + `name`).
- COMPONENT / COMPONENT_SET — тот же скрипт. Variant-имена (`prop=value`, `text#123:1`) — контракт Figma: менять только с явного согласия пользователя, иначе ломаются свойства компонента.
- `missing` непустой — докладывать в итог, не замалчивать.
- Инстансы внешних библиотек: переименование допустимо (это имя слоя на канвасе), но main component не трогать.

## Типовые отказы (полный список — figma-use)

| Ошибка | Причина / фикс |
|---|---|
| `Setting figma.currentPage is not supported` | sync-сеттер; только `await figma.setCurrentPageAsync(page)` |
| `no such property 'loadAllPagesAsync'` | API недоступен в use_figma; переключать страницы по одной |
| Пустой ответ | не было `return`; `console.log` не возвращается |
| `not implemented` | вызван `figma.notify()` — убрать |
| `The node with id X does not exist` | id с другой страницы / устарел после detach — пере-найти через traversal |
| `safeToRetryWithoutCanvasRead: false` | сначала перечитать канвас, потом править |

## Проверка авторизации

При 403/ошибках доступа — `mcp__figma_official__whoami` (покажет хэндл, планы, сид). Если у пользователя нет прав на файл — сказать прямо; угадывать содержимое макета нельзя (правило «только факты»).