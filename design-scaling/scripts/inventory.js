// Инвентаризация макета для use_figma (только чтение).
// Перед запуском заменить ROOT_ID на id фрейма концепции (из ссылки: node-id=1-98 → '1:98').
// Возвращает частоты значений: текстовые стили, цвета, отступы, радиусы, обводки, эффекты,
// x-координаты левых краёв (для восстановления сетки) и список секций.
// Значения с count 1–2 рядом с частыми соседями — кандидаты в «разнобой».

const ROOT_ID = '1:98';
const root = await figma.getNodeByIdAsync(ROOT_ID);
if (!root) throw new Error('Нет узла ' + ROOT_ID);

const hex = c => '#' + [c.r, c.g, c.b].map(v => Math.round(v * 255).toString(16).padStart(2, '0')).join('').toUpperCase();
const bump = (map, key, example) => {
  const e = map.get(key) || { count: 0, examples: [] };
  e.count++;
  if (e.examples.length < 3 && example && !e.examples.includes(example)) e.examples.push(example);
  map.set(key, e);
};
const top = (map, n = 40) => [...map.entries()].sort((a, b) => b[1].count - a[1].count).slice(0, n)
  .map(([k, v]) => ({ v: k, n: v.count, ex: v.examples }));
const sectionOf = n => { let p = n; while (p.parent && p.parent.id !== root.id) p = p.parent; return p.name.trim(); };
const absX = n => Math.round(n.absoluteTransform[0][2] - root.absoluteTransform[0][2]);

const text = new Map(), textFill = new Map(), fills = new Map(), strokes = new Map(),
  pad = new Map(), gap = new Map(), radius = new Map(), effects = new Map(), leftX = new Map(),
  imgRatio = new Map();

const nodes = root.findAll(() => true);
for (const n of nodes) {
  if (!n.visible) continue;
  const where = sectionOf(n) + ' / ' + n.name.trim();
  if (n.type === 'TEXT') {
    const segs = n.getStyledTextSegments(['fontName', 'fontSize', 'lineHeight', 'letterSpacing', 'textCase', 'fills']);
    for (const s of segs) {
      const lh = s.lineHeight.unit === 'AUTO' ? 'auto' : (s.lineHeight.unit === 'PERCENT' ? s.lineHeight.value.toFixed(0) + '%' : s.lineHeight.value.toFixed(1) + 'px');
      const ls = s.letterSpacing.unit === 'PERCENT' ? s.letterSpacing.value.toFixed(1) + '%' : s.letterSpacing.value.toFixed(2) + 'px';
      bump(text, `${s.fontName.family} ${s.fontName.style} ${s.fontSize}/${lh} ls ${ls}${s.textCase !== 'ORIGINAL' ? ' ' + s.textCase : ''}`, where);
      const f = s.fills.find(p => p.type === 'SOLID' && p.visible !== false);
      if (f) bump(textFill, hex(f.color) + (f.opacity < 1 ? ' @' + f.opacity.toFixed(2) : ''), where);
    }
    bump(leftX, absX(n), where);
    continue;
  }
  if ('fills' in n && Array.isArray(n.fills)) for (const f of n.fills) {
    if (f.visible === false) continue;
    if (f.type === 'SOLID') bump(fills, hex(f.color) + (f.opacity < 1 ? ' @' + f.opacity.toFixed(2) : ''), where);
    if (f.type === 'IMAGE') bump(imgRatio, (n.width / n.height).toFixed(2) + ` (${Math.round(n.width)}×${Math.round(n.height)})`, where);
    if (f.type.startsWith('GRADIENT')) bump(fills, f.type, where);
  }
  if ('strokes' in n && n.strokes.length && n.strokeWeight !== figma.mixed) {
    const s = n.strokes.find(p => p.type === 'SOLID' && p.visible !== false);
    if (s) {
      const sides = ('strokeTopWeight' in n) ? [n.strokeTopWeight, n.strokeRightWeight, n.strokeBottomWeight, n.strokeLeftWeight].join('/') : n.strokeWeight;
      bump(strokes, `${hex(s.color)}${s.opacity < 1 ? ' @' + s.opacity.toFixed(2) : ''} w ${sides}`, where);
    }
  }
  if ('layoutMode' in n && n.layoutMode !== 'NONE') {
    bump(pad, `${n.paddingTop}/${n.paddingRight}/${n.paddingBottom}/${n.paddingLeft}`, where);
    if (n.primaryAxisAlignItems !== 'SPACE_BETWEEN') bump(gap, `${n.layoutMode[0]} ${n.itemSpacing}`, where);
  }
  if ('cornerRadius' in n && n.cornerRadius !== figma.mixed && n.cornerRadius > 0) bump(radius, n.cornerRadius, where);
  if ('effects' in n && n.effects.length) for (const e of n.effects) if (e.visible !== false)
    bump(effects, `${e.type} r${e.radius}${e.offset ? ` ${e.offset.x},${e.offset.y}` : ''}${e.color ? ' ' + hex(e.color) + ' @' + e.color.a.toFixed(2) : ''}`, where);
}

const sections = root.children.map(c => ({
  id: c.id, name: c.name.trim(), y: Math.round(c.y), h: Math.round(c.height),
  bg: ('fills' in c && Array.isArray(c.fills) && c.fills.find(f => f.type === 'SOLID' && f.visible !== false)) ? hex(c.fills.find(f => f.type === 'SOLID').color) : 'none',
  layout: 'layoutMode' in c ? c.layoutMode : '-',
  pad: 'layoutMode' in c && c.layoutMode !== 'NONE' ? `${c.paddingTop}/${c.paddingRight}/${c.paddingBottom}/${c.paddingLeft}` : '-',
}));

const out = {
  root: { name: root.name, w: root.width, h: root.height, grids: 'layoutGrids' in root ? root.layoutGrids : [] },
  nodes: nodes.length, sections,
  text: top(text, 50), textFill: top(textFill), fills: top(fills), strokes: top(strokes),
  padding: top(pad), gap: top(gap), radius: top(radius), effects: top(effects),
  leftX: top(leftX, 30), imageRatios: top(imgRatio, 20),
};
const size = JSON.stringify(out).length;
if (size > 60000) { for (const k of ['text', 'fills', 'padding', 'gap', 'leftX']) out[k] = out[k].map(r => ({ v: r.v, n: r.n, ex: r.ex.slice(0, 1) })); }
return out;
