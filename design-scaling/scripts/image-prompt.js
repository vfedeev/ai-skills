// Вставляет внутрь заглушки изображения текст промта для генерации — для use_figma.
// Зачем: картинки агент не генерирует. Он ставит заглушку и пишет промт прямо в неё, чтобы
// дизайнер видел, что должно быть в кадре, и мог сгенерировать картинку сам.
//
// Что делает с каждой заглушкой:
//  - RECTANGLE заменяет фреймом того же размера, места, заливок и радиусов (в прямоугольник
//    текст не вставить). INSTANCE не трогает — вернёт ошибку: заменить заглушкой-фреймом;
//  - удаляет прежний текст «Промт» и вставляет новый: подпись + промт;
//  - подбирает самый крупный стиль «Промт / …», при котором текст помещается в заглушку
//    с отступами. Размер шрифта руками не задаётся: любое типографское свойство отвязывает
//    текст от стиля. Не влез даже в самый мелкий — overflow: true, промт сократить;
//  - отступ — переменная коллекции «Отступы» с именем на PAD_PREFIX (самая крупная, что
//    ≤ 8% меньшей стороны) и привязывается к паддингам, если у заглушки нет других детей;
//    иначе текст ставится абсолютно с тем же отступом. Только PAD_PREFIX: иначе по
//    совпадению значения в паддинг попадёт «хедер/верх» или «список/текст-линия»;
//  - повторный запуск по той же заглушке заменяет промт и снова раскладывает его auto layout;
//  - цвет текста привязывает к роли TEXT_ROLE; роли нет — noRole: true, привязать по colors.md.
//    TEXT_ROLE выбрать контрастной к заливке заглушки (на сером `фото/подложка` бледная
//    второстепенная роль не читается — брать тёмную роль текста).
// Стилей «Промт / …» нет — создаёт их (Inter, служебные, не для макета) и называет в createdStyles.
//
// Использование: вставить в скрипт use_figma, заполнить ITEMS и вызвать
//   return await placePrompts(ITEMS)
// После — color-audit.js по фрейму страницы: заглушки и промты тоже должны быть привязаны.

const ITEMS = [
  // { id: '<id заглушки>', caption: 'Фото: интерьер галереи, общий план · 16:9', prompt: '<english prompt>' },
];
const PROMPT_STYLE_PREFIX = 'Промт /';
const DEFAULT_SIZES = { L: 24, M: 18, S: 14, XS: 11, XXS: 8 }; // если стилей ещё нет
const FONT = { family: 'Inter', style: 'Regular' };
const TEXT_ROLE = 'текст/основной'; // тёмная роль текста, контрастная к заливке заглушки
const SPACING_COLLECTION = 'Отступы';
const PAD_PREFIX = 'отступ/'; // какие переменные годятся в паддинг заглушки
const RADII = ['topLeftRadius', 'topRightRadius', 'bottomLeftRadius', 'bottomRightRadius'];

async function rectToFrame(r) {
  const p = r.parent, i = p.children.indexOf(r);
  const f = figma.createFrame();
  p.insertChild(i, f);
  f.name = r.name;
  f.resize(r.width, r.height);
  f.fills = r.fills; f.strokes = r.strokes; f.strokeWeight = r.strokeWeight; f.effects = r.effects;
  f.opacity = r.opacity; f.visible = r.visible;
  for (const k of RADII) {
    f[k] = r[k];
    const b = r.boundVariables && r.boundVariables[k];
    if (b) { const v = await figma.variables.getVariableByIdAsync(b.id); if (v) f.setBoundVariable(k, v); }
  }
  const inAL = 'layoutMode' in p && p.layoutMode !== 'NONE';
  if (inAL && r.layoutPositioning !== 'ABSOLUTE') {
    f.layoutAlign = r.layoutAlign; f.layoutGrow = r.layoutGrow;
    try { f.layoutSizingHorizontal = r.layoutSizingHorizontal; } catch (e) {}
    try { f.layoutSizingVertical = r.layoutSizingVertical; } catch (e) {}
  } else {
    if (inAL) f.layoutPositioning = 'ABSOLUTE';
    f.relativeTransform = r.relativeTransform; f.constraints = r.constraints;
  }
  r.remove();
  return f;
}

async function placePrompts(items) {
  await figma.loadFontAsync(FONT);
  let styles = (await figma.getLocalTextStylesAsync()).filter(s => s.name.startsWith(PROMPT_STYLE_PREFIX));
  const createdStyles = [];
  if (!styles.length) {
    for (const [k, size] of Object.entries(DEFAULT_SIZES)) {
      const s = figma.createTextStyle();
      s.name = `${PROMPT_STYLE_PREFIX} ${k}`;
      s.fontName = FONT; s.fontSize = size; s.lineHeight = { unit: 'PERCENT', value: 130 };
      s.description = 'Служебный: промт внутри заглушки изображения. Не для макета.';
      styles.push(s); createdStyles.push(s.name);
    }
  }
  for (const s of styles) await figma.loadFontAsync(s.fontName);
  styles.sort((a, b) => b.fontSize - a.fontSize);

  const role = (await figma.variables.getLocalVariablesAsync('COLOR')).find(v => v.name === TEXT_ROLE);
  const spColl = (await figma.variables.getLocalVariableCollectionsAsync()).find(c => c.name === SPACING_COLLECTION);
  const spacing = [];
  if (spColl) for (const id of spColl.variableIds) {
    const v = await figma.variables.getVariableByIdAsync(id);
    const val = v && v.resolvedType === 'FLOAT' ? v.valuesByMode[spColl.defaultModeId] : null;
    if (typeof val === 'number' && v.name.startsWith(PAD_PREFIX)) spacing.push({ v, val });
  }

  const results = [];
  for (const it of items) {
    let ph = await figma.getNodeByIdAsync(it.id);
    if (!ph) { results.push({ id: it.id, error: 'узел не найден' }); continue; }
    if (ph.type === 'INSTANCE') { results.push({ id: it.id, error: 'инстанс: внутрь не вставить — заменить заглушкой-фреймом' }); continue; }
    if (ph.type === 'RECTANGLE') ph = await rectToFrame(ph);
    if (ph.type !== 'FRAME') { results.push({ id: it.id, error: 'тип ' + ph.type + ': нужен FRAME или RECTANGLE' }); continue; }

    for (const old of ph.findChildren(n => n.name === 'Промт')) old.remove();
    const w = ph.width, h = ph.height;
    const sp = spacing.filter(s => s.val <= Math.min(w, h) * 0.08).sort((a, b) => b.val - a.val)[0];
    const pad = sp ? sp.val : Math.max(4, Math.round(Math.min(w, h) * 0.06));
    // пустая заглушка — своя auto layout раскладка; после прошлого запуска она уже VERTICAL
    const useAL = ph.children.length === 0;
    ph.clipsContent = true;
    if (useAL) {
      if (ph.layoutMode !== 'VERTICAL') ph.layoutMode = 'VERTICAL';
      ph.primaryAxisSizingMode = 'FIXED'; ph.counterAxisSizingMode = 'FIXED';
      ph.resize(w, h);
      for (const k of ['paddingTop', 'paddingBottom', 'paddingLeft', 'paddingRight']) {
        if (ph.boundVariables && ph.boundVariables[k]) ph.setBoundVariable(k, null);
        ph[k] = pad;
        if (sp) ph.setBoundVariable(k, sp.v);
      }
    }

    const t = figma.createText();
    t.name = 'Промт';
    ph.appendChild(t);
    t.characters = [it.caption, it.prompt].filter(Boolean).join('\n');
    if (useAL) { t.textAutoResize = 'HEIGHT'; t.layoutSizingHorizontal = 'FILL'; }
    else {
      if (ph.layoutMode !== 'NONE') t.layoutPositioning = 'ABSOLUTE';
      t.resize(Math.max(1, w - 2 * pad), 10); t.textAutoResize = 'HEIGHT'; t.x = pad; t.y = pad;
    }
    if (role) t.fills = [figma.variables.setBoundVariableForPaint({ type: 'SOLID', color: { r: 0.5, g: 0.5, b: 0.5 } }, 'color', role)];

    let chosen = null;
    for (const s of styles) {
      await t.setTextStyleIdAsync(s.id);
      if (t.height <= h - 2 * pad) { chosen = s; break; }
    }
    results.push({
      id: ph.id, replacedRect: ph.id !== it.id ? it.id : undefined, textId: t.id,
      style: (chosen || styles[styles.length - 1]).name, overflow: !chosen,
      pad, padVar: sp ? sp.v.name : null, noRole: !role,
    });
  }
  // overflow — промт не влез даже в самый мелкий стиль: сократить промт (не подпись) и запустить снова
  return { results, createdStyles };
}
