# БЭМ-аудитор — нейминг слоёв Figma по БЭМ и UIkit

Скилл для Hermes Agent: аудит и безопасное переименование слоёв в Figma-макетах по методологии БЭМ, со справочником по UIkit и детерминированным валидатором имён.

## Что делает

- **Аудит**: снимает дерево слоёв фрейма/страницы через Figma MCP, находит автогенерацию Figma (`Frame 12`, `Vector`), невалидные БЭМ-имена и выдуманные UIkit-классы, выдаёт таблицу корректур `узел (id) | тип | было | стало | почему`
- **Переименование**: применяет только явно утверждённый пользователем список, батчами ≤50 пар с верификацией результата; ничего не меняет без «да»
- **Справочник**: отвечает по вопросам БЭМ (block/element/modifier, `__`, `_`, `--`, классическая и two-dashes схемы) и UIkit (`uk-*` классы, состояния) только по reference-файлам с источниками
- **Проверка имён без Figma**: конвейерный валидатор — список имён на вход, JSON с ошибками/предупреждениями/автоименами на выход

Правила вёрстки слоёв защищены от разрушительных операций: запрет менять auto-layout при переименовании, запрет удалять контейнер с непроверенными детьми, обязательная верификация `absoluteTransform` при wrapper-фреймах.

## Триггеры

«Проверь нейминг слоёв в этом фрейме», «приведи слои к БЭМ», «переименуй фреймы по списку», «что не так с названиями в макете», вопросы про БЭМ-схемы именования, классы и состояния UIkit.

## Комплект

| Файл | Назначение |
|------|-----------|
| `SKILL.md` | режимы (справочник / аудит / переименование), железные правила, workflow из 7 шагов |
| `references/bem-naming.md` | канон именования: обе схемы (classic, two-dashes), антипаттерны, шаблоны имён по типам элементов макета |
| `references/uikit.md` | словарь UIkit 3: классы, модификаторы, состояния + таблица частых выдуманных имён |
| `references/figma-workflow.md` | готовые JS-скрипты для Figma Plugin API (dump tree, rename batch, wrapper-фрейм), питфоллы MCP, уроки боевых прогонов |
| `scripts/validate_bem_name.py` | детерминированный валидатор БЭМ-имён (stdlib, JSON-вывод, детект автоимён Figma) |

## Требования

- Hermes Agent; для режимов «аудит» и «переименование» — Figma MCP (`use_figma`, `get_metadata`, `get_screenshot`)
- Python 3.8+ (stdlib) — для валидатора; Figma не требуется

## Установка

### Через git

```bash
git clone https://github.com/vfedeev/ai-skills.git
cd ai-skills
cp -r bem-auditor ~/.hermes/skills/
```

### Из ZIP-архива

```bash
curl -L -o bem-auditor.zip https://github.com/vfedeev/ai-skills/releases/latest/download/ai-skills-v3.6.0.zip
unzip bem-auditor.zip
cp -r ai-skills-v3.6.0/bem-auditor ~/.hermes/skills/
```

## Быстрый старт

```bash
# Проверить список имён слоёв (выгрузите имена из Figma в names.txt):
cat names.txt | python3 ~/.hermes/skills/bem-auditor/scripts/validate_bem_name.py --scheme classic --figma

# Или несколько имён аргументами:
python3 validate_bem_name.py --scheme two-dashes hero__image menu__item--active hero__a__b
```

В чате Hermes: пришлите ссылку вида `figma.com/design/<fileKey>/…?node-id=…` и скажите «проаудировал имена слоёв по БЭМ» — получите таблицу корректур без единой правки; переименование — только после вашего «да» на конкретный список.

## Лицензия

MIT. Автор — Vladimir F. Правила БЭМ — источники bem.info / getbem.com, словарь UIkit — getuikit.com.
