// Привязывает все цвета внутри узлов к ролевым переменным — для use_figma.
// Что привязывает: сплошные заливки, обводки, цвет текста (по сегментам), стопы градиентов,
// цвета теней (DROP_SHADOW, INNER_SHADOW). Изображения и видео не трогает. Скрытые слои тоже
// привязывает: их включают свойства компонентов. Цвет, привязанный к переменной НЕ из
// коллекции ролей (примитив палитры, чужая библиотека, удалённая переменная), перепривязывает.
//
// Как подбирает роль: берёт режим коллекции ROLE_COLLECTION, в котором стоит узел (ближайший
// явный режим у предков, включая страницу), и ищет роль с тем же цветом и прозрачностью,
// у которой scopes разрешают это свойство. Совпадений несколько — сначала роли группы
// компонента-предка («кнопка-стекло/…»), потом по порядку PREFER.
// Прозрачность слоя заливки переносится в переменную: после привязки opacity заливки = 1.
//
// ПЕРЕД ЗАПУСКОМ:
//  1. Задать режим темы каждой секции (setExplicitVariableModeForCollection). Без этого белый
//     текст тёмной секции привяжется к «светлой» роли с тем же цветом.
//  2. Заменить ROOT_IDS (все — с одной страницы; другая страница — отдельный вызов). Порядок вызовов: сначала страница UI-kit, потом макеты страниц —
//     иначе инстансы получат переопределения вместо наследования от компонента.
//  3. Подстроить PREFER под имена ролей из дизайн-правила.md. Завели новую роль — добавить
//     её префикс в PREFER, иначе она проиграет старой роли того же цвета.
//  DRY_RUN = true — ничего не пишет, но проверяет загрузку шрифтов: что упадёт в настоящем
//  запуске, упадёт и здесь. Слои инстансов, которые унаследуют привязку от компонента,
//  в DRY_RUN не считаются.
//
// Возвращает:
//  bound — сколько цветов привязано (в DRY_RUN — будет привязано);
//  missing — цвета без подходящей роли: { color, scope, mode, n, where, otherMode }. otherMode
//    не пусто — такой цвет есть в другом режиме: скорее всего, у секции не задан режим;
//  picked — где выбирал из нескольких ролей. byGroup = false — выбор только по PREFER;
//  usage — роль → сколько узлов → примеры. Совпадение по цвету не гарантирует смысл;
//  rebound — перепривязано по REBIND и с чужих переменных;
//  styled — узлы с цветовым стилем (fillStyleId и т. п.): не тронуты, решить вручную;
//  unbindable — цвета, которые Figma не даёт привязать (шум, NOISE);
//  failed — узлы, которые не удалось изменить. «font could not be loaded» — текст на
//    недоступном шрифте (см. references/colors.md, «Привязка цветов», шаг 4);
//  warnings — алиасы на коллекции с несколькими режимами и т. п.
// Цель — missing = [] и failed = [].

const ROOT_IDS = ['8:58'];
const ROLE_COLLECTION = 'Цвет';
const DRY_RUN = false;
// Узлы, которые в концепции нарисованы в другой теме, чем режим, в котором они стоят сейчас.
// Пример: компонент «Поле» склонирован из тёмной формы и лежит на UI-kit в режиме по умолчанию
// (Светлая) — белая обводка не совпадёт ни с одной светлой ролью. { '11:112': 'Тёмная' } —
// подбирать роли по значениям Тёмной; после привязки компонент сам перекрасится по режиму.
const DRAWN_IN = {};
// Перепривязка уже привязанного: [{ from: 'линия/акцент', to: 'иконка/основной',
// types: ['VECTOR', 'BOOLEAN_OPERATION'] }] — types необязателен.
const REBIND = [];
const PREFER = {
  TEXT_FILL: ['текст/', 'кнопка/текст'],
  STROKE_COLOR: ['линия/', 'поле/', 'кнопка'],
  FRAME_FILL: ['фон/', 'кнопка', 'фото/'],
  SHAPE_FILL: ['иконка/', 'текст/', 'линия/', 'фон/', 'декор/', 'фото/'],
  EFFECT_COLOR: ['тень/', 'эффект/'],
  ICON: ['иконка/', 'текст/', 'кнопка'], // векторы (VECTOR, BOOLEAN_OPERATION…) — и заливка, и обводка
};
// Общие группы ролей: родство с предком по ним не считается — иначе шеврон внутри поля
// с обводкой «линия/поле» получит «линия/акцент» того же цвета.
const GENERIC_GROUPS = ['фон', 'текст', 'линия', 'иконка', 'декор', 'фото', 'служебное'];

const EPS = 0.6 / 255, EPS_A = 0.01;
const hex = (c, a) => '#' + [c.r, c.g, c.b].map(v => Math.round(v * 255).toString(16).padStart(2, '0')).join('').toUpperCase()
  + (a !== undefined && a < 0.995 ? ' @' + a.toFixed(2) : '');
const same = (c, a, v) => Math.abs(c.r - v.r) < EPS && Math.abs(c.g - v.g) < EPS && Math.abs(c.b - v.b) < EPS && Math.abs(a - (v.a ?? 1)) < EPS_A;
const where = n => { const path = []; for (let p = n; p && p.type !== 'PAGE' && path.length < 3; p = p.parent) path.unshift(p.name.trim()); return path.join(' / ') + ' #' + n.id; };
const bump = (map, key, init, n) => { const e = map.get(key) || { ...init, n: 0, where: [] }; e.n++; if (e.where.length < 4) e.where.push(where(n)); map.set(key, e); };

// Все корни — с одной страницы, и на неё переключаемся: страница другого корня в dynamic-page
// обходится не целиком даже после loadAsync() (проверено: 182 узла из 273, без ошибки).
// Корни на разных страницах — отдельный вызов на каждую страницу.
const roots = [];
for (const id of ROOT_IDS) { const r = await figma.getNodeByIdAsync(id); if (!r) throw new Error('Нет узла ' + id); roots.push(r); }
const pageOf = n => { let p = n; while (p.type !== 'PAGE') p = p.parent; return p; };
const pages = [...new Set(roots.map(r => pageOf(r).id))];
if (pages.length > 1) throw new Error('ROOT_IDS на разных страницах: запустить отдельным вызовом на каждую страницу');
await figma.setCurrentPageAsync(pageOf(roots[0]));

// --- роли и их значения по режимам
const roleCol = (await figma.variables.getLocalVariableCollectionsAsync()).find(c => c.name === ROLE_COLLECTION);
if (!roleCol) throw new Error('Нет коллекции ' + ROLE_COLLECTION);
const vars = (await Promise.all(roleCol.variableIds.map(id => figma.variables.getVariableByIdAsync(id))))
  .filter(v => v && v.resolvedType === 'COLOR');
const varById = Object.fromEntries(vars.map(v => [v.id, v]));
const varByName = Object.fromEntries(vars.map(v => [v.name, v]));
const warnings = new Set();
const colCache = {};
const colOf = async id => colCache[id] || (colCache[id] = await figma.variables.getVariableCollectionByIdAsync(id));
// Значение роли в режиме роли → { r, g, b, a } или null. Разворачивает алиасы и «алиас +
// прозрачность». Алиас внутри коллекции ролей — тот же режим; в коллекцию с одним режимом —
// её режим; в чужую коллекцию с несколькими режимами — режим по умолчанию + предупреждение.
async function valueIn(v, modeId, depth = 0) {
  if (!v || depth > 10) return null;
  const c = await colOf(v.variableCollectionId);
  if (!c) { warnings.add(`${v.name}: нет коллекции`); return null; }
  const m = v.valuesByMode[modeId] !== undefined ? modeId : c.defaultModeId;
  return resolveValue(v.valuesByMode[m], v, m, depth);
}
async function resolveValue(val, owner, modeId, depth) {
  if (!val) return null;
  if (val.type === 'VARIABLE_ALIAS') {
    const t = await figma.variables.getVariableByIdAsync(val.id);
    if (!t) { warnings.add(`${owner.name}: алиас на удалённую переменную`); return null; }
    const c = await colOf(t.variableCollectionId);
    if (!c) { warnings.add(`${owner.name}: нет коллекции у ${t.name}`); return null; }
    if (c.id === roleCol.id) return valueIn(t, modeId, depth + 1);
    if (c.modes.length > 1) warnings.add(`${owner.name} → ${t.name}: коллекция «${c.name}» с несколькими режимами, взят режим по умолчанию`);
    return valueIn(t, c.defaultModeId, depth + 1);
  }
  if (val.color !== undefined && val.opacity !== undefined) { // VariableComposedColor
    const base = await resolveValue(val.color, owner, modeId, depth + 1);
    return base && { ...base, a: (base.a ?? 1) * val.opacity };
  }
  return 'r' in val ? val : null;
}
const table = {};
for (const m of roleCol.modes) table[m.modeId] = await Promise.all(vars.map(async v => ({ v, value: await valueIn(v, m.modeId) })));
const modeName = id => (roleCol.modes.find(m => m.modeId === id) || {}).name;
const allows = (v, scope) => v.scopes.includes(scope) || v.scopes.includes('ALL_SCOPES')
  || (scope.endsWith('_FILL') && v.scopes.includes('ALL_FILLS'));
const rank = (v, key) => { const i = (PREFER[key] || []).findIndex(p => v.name.startsWith(p)); return i < 0 ? 99 : i; };

const drawnIn = Object.fromEntries(Object.entries(DRAWN_IN).map(([id, name]) => {
  const m = roleCol.modes.find(x => x.name === name);
  if (!m) throw new Error(`DRAWN_IN: нет режима «${name}» в ${ROLE_COLLECTION}`);
  return [id, m.modeId];
}));
// Режим — по цепочке явных режимов предков, включая страницу: resolvedVariableModes Figma
// отдаёт только для узлов с привязками и у непривязанного узла вернёт «по умолчанию».
const modeOf = n => {
  for (let p = n; p; p = p.parent) {
    if (drawnIn[p.id]) return drawnIn[p.id];
    const m = p.explicitVariableModes && p.explicitVariableModes[roleCol.id];
    if (m) return m;
    if (p.type === 'PAGE') break;
  }
  return roleCol.defaultModeId;
};

// --- родство групп: «кнопка-стекло/фон» у предка → ребёнку сначала «кнопка-стекло/…»
const group = name => name.split('/')[0];
const committed = new Map(); // id узла → группы ролей, записанные в этом прогоне
const groupsOf = n => {
  if (committed.has(n.id)) return committed.get(n.id);
  const g = new Set();
  for (const prop of ['fills', 'strokes']) if (prop in n && Array.isArray(n[prop]))
    for (const p of n[prop]) { const id = p.boundVariables && p.boundVariables.color && p.boundVariables.color.id; if (id && varById[id]) g.add(group(varById[id].name)); }
  return g;
};
const nearGroups = n => {
  for (let p = n.parent; p && p.type !== 'PAGE'; p = p.parent) {
    const g = [...groupsOf(p)].filter(x => !GENERIC_GROUPS.includes(x));
    if (g.length) return new Set(g);
  }
  return new Set();
};
const VECTORS = ['VECTOR', 'BOOLEAN_OPERATION', 'STAR', 'POLYGON'];
const SHAPES = ['RECTANGLE', 'ELLIPSE', 'LINE', ...VECTORS];
const fillScope = n => n.type === 'TEXT' ? 'TEXT_FILL' : SHAPES.includes(n.type) ? 'SHAPE_FILL' : 'FRAME_FILL';

let bound = 0;
const picked = new Map(), missing = new Map(), usage = new Map(), rebound = new Map(),
  styled = new Map(), unbindable = new Map(), failed = [];

// подбор роли; ничего не записывает в счётчики — это делает commit после успешной записи
function pick(n, scope, color, alpha) {
  const mode = modeOf(n), near = nearGroups(n);
  const order = VECTORS.includes(n.type) && scope !== 'EFFECT_COLOR' ? 'ICON' : scope;
  const kin = v => near.has(group(v.name)) ? 0 : 1;
  const c = table[mode].filter(x => x.value && allows(x.v, scope) && same(color, alpha, x.value))
    .sort((a, b) => kin(a.v) - kin(b.v) || rank(a.v, order) - rank(b.v, order));
  if (c.length) return { v: c[0].v, alts: c.map(x => x.v.name), byGroup: kin(c[0].v) === 0, scope, color: hex(color, alpha) };
  const other = roleCol.modes.filter(m => m.modeId !== mode && table[m.modeId].some(x => x.value && allows(x.v, scope) && same(color, alpha, x.value))).map(m => m.name);
  bump(missing, `${hex(color, alpha)} ${scope}`, { color: hex(color, alpha), scope, mode: modeName(mode), otherMode: other }, n);
  return null;
}
// нужна ли перепривязка уже привязанного цвета: чужая переменная или правило REBIND
function rebindTarget(n, id) {
  const v = varById[id];
  if (!v) return 'чужая';
  const r = REBIND.find(x => x.from === v.name && (!x.types || x.types.includes(n.type)));
  if (r) { if (!varByName[r.to]) throw new Error('REBIND: нет роли ' + r.to); return varByName[r.to]; }
  return null;
}

// план по массиву красок: { next, picks[] } или null, если менять нечего
function planPaints(n, paints, scope) {
  const picks = [];
  const choose = (color, alpha, boundId) => {
    if (boundId) {
      const t = rebindTarget(n, boundId);
      if (!t) return null;
      if (t !== 'чужая') { picks.push({ v: t, alts: [t.name], byGroup: true, scope, color: hex(color, alpha), rebind: true }); return t; }
    }
    const p = pick(n, scope, color, alpha);
    if (p) { if (boundId) p.rebind = true; picks.push(p); }
    return p && p.v;
  };
  const next = paints.map(p => {
    if (p.visible === false) return p;
    const id = p.boundVariables && p.boundVariables.color && p.boundVariables.color.id;
    if (p.type === 'SOLID') {
      const v = choose(p.color, p.opacity ?? 1, id);
      if (!v) return p;
      const { boundVariables, ...raw } = p;
      return figma.variables.setBoundVariableForPaint({ ...raw, opacity: 1 }, 'color', v);
    }
    if (p.type.startsWith('GRADIENT')) {
      const stops = p.gradientStops.map(s => {
        const sid = s.boundVariables && s.boundVariables.color && s.boundVariables.color.id;
        const v = choose(s.color, s.color.a, sid);
        return v ? { ...s, boundVariables: { color: { type: 'VARIABLE_ALIAS', id: v.id } } } : s;
      });
      return { ...p, gradientStops: stops };
    }
    return p;
  });
  return picks.length ? { next, picks } : null;
}
function commit(n, picks) {
  for (const p of picks) {
    bound++;
    if (!committed.has(n.id)) committed.set(n.id, new Set(groupsOf(n)));
    committed.get(n.id).add(group(p.v.name));
    const u = usage.get(p.v.name) || { role: p.v.name, n: 0, ex: [] };
    u.n++; if (u.ex.length < 3) u.ex.push(p.scope + ': ' + where(n)); usage.set(p.v.name, u);
    if (p.alts.length > 1) {
      const key = `${p.color} ${p.scope} → ${p.v.name}`;
      const e = picked.get(key) || { choice: key, from: p.alts, byGroup: p.byGroup, n: 0, ex: where(n) }; e.n++; picked.set(key, e);
    }
    if (p.rebind) bump(rebound, p.v.name, { to: p.v.name }, n);
  }
}
const hasStyle = id => typeof id === 'string' && id !== '';
const writeFills = async (n, next) => {
  if (next.some(p => p.type === 'PATTERN') && 'setFillsAsync' in n) await n.setFillsAsync(next); else n.fills = next;
};

async function bindNode(n) {
  const picks = [];
  try {
    if (n.type === 'TEXT') {
      const segs = n.getStyledTextSegments(['fills', 'fontName', 'fillStyleId']);
      const plans = [];
      for (const s of segs) {
        if (hasStyle(s.fillStyleId)) { bump(styled, 'текст: цветовой стиль', { what: 'текст: цветовой стиль' }, n); continue; }
        const pl = planPaints(n, s.fills, 'TEXT_FILL');
        if (pl) plans.push({ s, ...pl });
      }
      if (plans.length) {
        // шрифты — только у изменяемых сегментов; в DRY_RUN тоже, чтобы увидеть будущие отказы
        for (const f of new Set(plans.map(x => JSON.stringify(x.s.fontName)))) await figma.loadFontAsync(JSON.parse(f));
        if (!DRY_RUN) for (const x of plans) n.setRangeFills(x.s.start, x.s.end, x.next);
        for (const x of plans) picks.push(...x.picks);
      }
    } else if ('fills' in n && Array.isArray(n.fills) && n.fills.length) {
      if (hasStyle(n.fillStyleId)) bump(styled, 'заливка: цветовой стиль', { what: 'заливка: цветовой стиль' }, n);
      else { const pl = planPaints(n, n.fills, fillScope(n)); if (pl) { if (!DRY_RUN) await writeFills(n, pl.next); picks.push(...pl.picks); } }
    }
    if ('strokes' in n && n.strokes.length) {
      if (hasStyle(n.strokeStyleId)) bump(styled, 'обводка: цветовой стиль', { what: 'обводка: цветовой стиль' }, n);
      else { const pl = planPaints(n, n.strokes, 'STROKE_COLOR'); if (pl) { if (!DRY_RUN) n.strokes = pl.next; picks.push(...pl.picks); } }
    }
    if ('effects' in n && n.effects.length) {
      if (hasStyle(n.effectStyleId)) bump(styled, 'эффект: стиль эффекта', { what: 'эффект: стиль эффекта' }, n);
      else {
        const ep = [];
        const next = n.effects.map(e => {
          if (e.visible === false || !e.color) return e;
          if (e.type !== 'DROP_SHADOW' && e.type !== 'INNER_SHADOW') { bump(unbindable, e.type + ' ' + hex(e.color, e.color.a), { what: e.type, color: hex(e.color, e.color.a) }, n); return e; }
          const id = e.boundVariables && e.boundVariables.color && e.boundVariables.color.id;
          let v = null;
          if (id) { const t = rebindTarget(n, id); if (!t) return e; if (t !== 'чужая') { v = t; ep.push({ v, alts: [t.name], byGroup: true, scope: 'EFFECT_COLOR', color: hex(e.color, e.color.a), rebind: true }); } }
          if (!v) { const p = pick(n, 'EFFECT_COLOR', e.color, e.color.a); if (!p) return e; if (id) p.rebind = true; ep.push(p); v = p.v; }
          return figma.variables.setBoundVariableForEffect(JSON.parse(JSON.stringify(e)), 'color', v);
        });
        if (ep.length) { if (!DRY_RUN) n.effects = next; picks.push(...ep); }
      }
    }
    commit(n, picks);
  } catch (e) { failed.push(where(n) + ': ' + String(e).slice(0, 140)); }
}

// Проход 1 — всё, кроме инстансов и их содержимого (компоненты, секции).
// Проход 2 — инстансы и их слои: после прохода 1 большинство уже наследует привязку.
// В DRY_RUN проход 1 ничего не пишет, поэтому слой инстанса, чей источник (последний сегмент
// id «I…;…») уже запланирован, пропускаем — в настоящем запуске он унаследует привязку.
const inInstance = n => { for (let p = n; p && p.type !== 'PAGE'; p = p.parent) if (p.type === 'INSTANCE') return true; return false; };
const seen = new Set();
for (const pass of [false, true]) for (const root of roots) {
  const nodes = root.type === 'PAGE' ? root.findAll(() => true) : [root, ...root.findAll(() => true)];
  for (const n of nodes) {
    if (inInstance(n) !== pass || seen.has(n.id)) continue;
    seen.add(n.id);
    if (DRY_RUN && pass) {
      if (n.id.includes(';') && committed.has(n.id.split(';').pop())) continue;
      if (n.type === 'INSTANCE') { const main = await n.getMainComponentAsync(); if (main && committed.has(main.id)) continue; }
    }
    await bindNode(n);
  }
}
const list = m => [...m.values()].sort((a, b) => b.n - a.n);
return { dryRun: DRY_RUN, bound, missing: list(missing).slice(0, 40), picked: list(picked).slice(0, 20),
  usage: list(usage), rebound: list(rebound), styled: list(styled), unbindable: list(unbindable),
  failed: failed.slice(0, 30), failedCount: failed.length, warnings: [...warnings] };
