// Аудит привязки цветов к ролевым переменным для use_figma (только чтение).
// Перед запуском заменить ROOT_IDS на id проверяемых узлов: фрейм страницы, страница UI-kit,
// отдельный компонент. Все узлы — с одной страницы; другая страница — отдельный вызов.
// Проверяет у каждого узла, включая скрытые (их включают свойства компонентов): заливки,
// обводки, цвет текста по сегментам, стопы градиентов, цвета теней. Изображения и видео
// не проверяются.
// «Привязан» = привязан к переменной из коллекции ROLE_COLLECTION. Привязка к примитиву палитры,
// к чужой библиотеке или к удалённой переменной считается непривязанной (поле elsewhere).
//
// Возвращает:
//   total, bound — сколько цветовых значений и сколько из них привязано к ролям;
//   unbound — непривязанные, сгруппированы по «цвет + свойство + режим секции»:
//     { color, kind, mode, n, remote, elsewhere, where[] }. remote — сколько из них внутри
//     инстансов внешних библиотек: их тоже привязывают (переопределением в инстансе);
//   truncated — список unbound обрезан, есть ещё группы;
//   styled — цвета из цветовых стилей (fillStyleId и т. п.): решить вручную;
//   unbindable — цвета, которые Figma не даёт привязать (эффект NOISE): в цель не входят.
// Цель: unbound = []. На фрейме концепции (где ничего не привязано) unbound — полный список
// цветов концепции по местам употребления: из него собирают роли на этапе А.

const ROOT_IDS = ['8:58'];
const ROLE_COLLECTION = 'Цвет';
const LIMIT = 60;

const hex = (c, a) => '#' + [c.r, c.g, c.b].map(v => Math.round(v * 255).toString(16).padStart(2, '0')).join('').toUpperCase()
  + (a !== undefined && a < 0.995 ? ' @' + a.toFixed(2) : '');
// Все корни — с одной страницы, и на неё переключаемся: страница другого корня в dynamic-page
// обходится не целиком даже после loadAsync() (проверено: 182 узла из 273, без ошибки).
// Корни на разных страницах — отдельный вызов на каждую страницу.
const roots = [];
for (const id of ROOT_IDS) { const r = await figma.getNodeByIdAsync(id); if (!r) throw new Error('Нет узла ' + id); roots.push(r); }
const pageOf = n => { let p = n; while (p.type !== 'PAGE') p = p.parent; return p; };
const pages = [...new Set(roots.map(r => pageOf(r).id))];
if (pages.length > 1) throw new Error('ROOT_IDS на разных страницах: запустить отдельным вызовом на каждую страницу');
await figma.setCurrentPageAsync(pageOf(roots[0]));

const roleCol = (await figma.variables.getLocalVariableCollectionsAsync()).find(c => c.name === ROLE_COLLECTION);
const roleIds = new Set(roleCol ? roleCol.variableIds : []);
const modeName = id => roleCol && (roleCol.modes.find(m => m.modeId === id) || {}).name;
const modeOf = n => {
  if (!roleCol) return '-';
  for (let p = n; p; p = p.parent) {
    const m = p.explicitVariableModes && p.explicitVariableModes[roleCol.id];
    if (m) return modeName(m);
    if (p.type === 'PAGE') break;
  }
  return modeName(roleCol.defaultModeId);
};
const mainCache = new Map();
async function isRemote(n) {
  for (let p = n; p && p.type !== 'PAGE'; p = p.parent) if (p.type === 'INSTANCE') {
    if (!mainCache.has(p.id)) { const m = await p.getMainComponentAsync(); mainCache.set(p.id, !!(m && m.remote)); }
    if (mainCache.get(p.id)) return true;
  }
  return false;
}
const where = n => { const path = []; for (let p = n; p && p.type !== 'PAGE' && path.length < 3; p = p.parent) path.unshift(p.name.trim()); return path.join(' / ') + ' #' + n.id; };
const SHAPES = ['RECTANGLE', 'ELLIPSE', 'LINE', 'VECTOR', 'BOOLEAN_OPERATION', 'STAR', 'POLYGON'];
const fillKind = n => n.type === 'TEXT' ? 'текст' : SHAPES.includes(n.type) ? 'заливка фигуры' : 'заливка фрейма';

let total = 0, bound = 0;
const unbound = new Map(), styled = new Map(), unbindable = new Map();
async function note(n, kind, color, alpha, binding) {
  total++;
  const id = binding && binding.id;
  if (id && roleIds.has(id)) { bound++; return; }
  const mode = modeOf(n), key = `${hex(color, alpha)} | ${kind} | ${mode}`;
  const e = unbound.get(key) || { color: hex(color, alpha), kind, mode, n: 0, remote: 0, elsewhere: 0, where: [] };
  e.n++; if (id) e.elsewhere++; if (await isRemote(n)) e.remote++;
  if (e.where.length < 6) e.where.push(where(n));
  unbound.set(key, e);
}
async function checkPaints(n, kind, paints) {
  if (!Array.isArray(paints)) return;
  for (const p of paints) {
    if (p.visible === false) continue;
    if (p.type === 'SOLID') await note(n, kind, p.color, p.opacity ?? 1, p.boundVariables && p.boundVariables.color);
    else if (p.type.startsWith('GRADIENT')) for (const s of p.gradientStops)
      await note(n, kind + ' (градиент)', s.color, s.color.a, s.boundVariables && s.boundVariables.color);
  }
}
const mark = (map, key, n) => { const e = map.get(key) || { what: key, n: 0, where: [] }; e.n++; if (e.where.length < 4) e.where.push(where(n)); map.set(key, e); };
const hasStyle = id => typeof id === 'string' && id !== '';

const seen = new Set();
for (const root of roots) {
  const nodes = root.type === 'PAGE' ? root.findAll(() => true) : [root, ...root.findAll(() => true)];
  for (const n of nodes) {
    if (seen.has(n.id)) continue;
    seen.add(n.id);
    if (n.type === 'TEXT') {
      for (const s of n.getStyledTextSegments(['fills', 'fillStyleId']))
        if (hasStyle(s.fillStyleId)) mark(styled, 'текст: цветовой стиль', n); else await checkPaints(n, 'текст', s.fills);
    } else if ('fills' in n) {
      if (hasStyle(n.fillStyleId)) mark(styled, 'заливка: цветовой стиль', n); else await checkPaints(n, fillKind(n), n.fills);
    }
    if ('strokes' in n && n.strokes.length) {
      if (hasStyle(n.strokeStyleId)) mark(styled, 'обводка: цветовой стиль', n); else await checkPaints(n, 'обводка', n.strokes);
    }
    if ('effects' in n && n.effects.length) {
      if (hasStyle(n.effectStyleId)) { mark(styled, 'эффект: стиль эффекта', n); continue; }
      for (const e of n.effects) {
        if (e.visible === false || !e.color) continue;
        if (e.type === 'DROP_SHADOW' || e.type === 'INNER_SHADOW') await note(n, 'тень', e.color, e.color.a, e.boundVariables && e.boundVariables.color);
        else mark(unbindable, e.type + ' ' + hex(e.color, e.color.a), n);
      }
    }
  }
}
const list = [...unbound.values()].sort((a, b) => b.n - a.n);
return { nodes: seen.size, total, bound, unboundCount: list.reduce((s, e) => s + e.n, 0), truncated: list.length > LIMIT,
  unbound: list.slice(0, LIMIT), styled: [...styled.values()], unbindable: [...unbindable.values()],
  ...(roleCol ? {} : { note: `Нет коллекции «${ROLE_COLLECTION}»: все цвета считаются непривязанными` }) };
