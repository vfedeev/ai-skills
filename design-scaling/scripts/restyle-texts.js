// Пересоздаёт тексты внутри узла с текстовыми стилями UI-kit.
// Зачем: шрифты концепции часто установлены только у дизайнера локально, и use_figma
// не может ни загрузить их, ни менять такие тексты — даже цвет. Клоны секций с ними можно
// двигать и удалять, но не редактировать и не перекрашивать. Функция заменяет каждый текст новым:
// те же символы, заливки, размеры, место в auto layout, но со стилем из UI-kit.
// Потом дизайнер меняет гарнитуру в стилях на оригинальную — и весь макет обновляется.
//
// Использование: вставить функцию в скрипт use_figma и вызвать
//   const res = await restyleTexts(node)  // → { map: { oldId: newId }, unavailableStyles, skipped, … }
// Сразу после — bind-colors.js по тому же узлу: цвета новых текстов скопированы «сырыми».
// STYLE_KEY подстроить под свою шкалу из дизайн-правила.md.

const STYLE_KEY = (family, style, size, textCase) => {
  const serif = /Ivy|Presto|Serif/i.test(family);
  const w = /Demi|Semi|Bold/i.test(style) ? 'b' : /Medium/i.test(style) ? 'm' : 'r';
  if (serif) return size >= 100 ? 'Display / Hero' : size >= 40 ? 'Serif / L' : size >= 25 ? 'Serif / M' : 'Serif / S';
  if (size >= 100) return 'Display / Число';
  if (size >= 60) return 'Display / L';
  if (size >= 18) return 'Текст / L';
  if (size >= 15) {
    if (textCase === 'UPPER') return w === 'b' ? 'Ссылка / CAPS' : 'Подпись / CAPS';
    return w === 'r' ? 'Текст / M' : 'Текст / M акцент';
  }
  return size >= 13 ? 'Текст / S' : 'Текст / XS';
};

async function restyleTexts(root) {
  const styles = await figma.getLocalTextStylesAsync();
  // имена сравниваются без пробелов вокруг «/»: «Текст/M» и «Текст / M» — один стиль
  const norm = s => s.replace(/\s*\/\s*/g, '/').trim();
  const byName = Object.fromEntries(styles.map(s => [norm(s.name), s]));
  // стиль на недоступном шрифте (дизайнер уже вернул оригинал) — не падать, а сообщить
  const unavailable = new Set();
  for (const s of styles) { try { await figma.loadFontAsync(s.fontName); } catch (e) { unavailable.add(s.name + ' — ' + s.fontName.family + ' ' + s.fontName.style); byName[norm(s.name)] = null; } }
  await figma.loadFontAsync({ family: 'Inter', style: 'Regular' });
  const texts = root.type === 'TEXT' ? [root] : root.findAll(n => n.type === 'TEXT');
  const map = {}, missing = new Set(), skipped = [];
  for (const t of texts) {
    const segs = t.getStyledTextSegments(['fontName', 'fontSize', 'textCase', 'fills', 'textDecoration']);
    // нужен стиль на недоступном шрифте — текст не трогаем: новый набрать им нельзя
    const blocked = segs.map(s => STYLE_KEY(s.fontName.family, s.fontName.style, s.fontSize, s.textCase)).filter(k => byName[norm(k)] === null);
    if (blocked.length) { skipped.push(t.id + ' «' + t.characters.slice(0, 30) + '» → ' + [...new Set(blocked)].join(', ')); continue; }
    const parent = t.parent, idx = parent.children.indexOf(t);
    const n = figma.createText();
    parent.insertChild(idx, n);
    n.characters = t.characters;
    for (const s of segs) {
      const key = STYLE_KEY(s.fontName.family, s.fontName.style, s.fontSize, s.textCase);
      const st = byName[norm(key)];
      if (!st) { missing.add(key); continue; }
      await n.setRangeTextStyleIdAsync(s.start, s.end, st.id);
      n.setRangeFills(s.start, s.end, s.fills);
      if (s.textDecoration !== 'NONE') n.setRangeTextDecoration(s.start, s.end, s.textDecoration);
    }
    n.name = t.name;
    // ширину колонок в концепции часто держат min/max — без них текст растекается на всю строку
    n.minWidth = t.minWidth; n.maxWidth = t.maxWidth; n.minHeight = t.minHeight; n.maxHeight = t.maxHeight;
    // НЕ копировать paragraphSpacing, lineHeight и прочую типографику: установка любого
    // такого свойства (даже в то же значение) отвязывает текст от стиля. Отбивку абзацев
    // задавать в самом текстовом стиле.
    n.textAlignHorizontal = t.textAlignHorizontal;
    n.textAlignVertical = t.textAlignVertical;
    n.opacity = t.opacity; n.visible = t.visible;
    const inAL = 'layoutMode' in parent && parent.layoutMode !== 'NONE';
    if (t.layoutPositioning === 'ABSOLUTE') n.layoutPositioning = 'ABSOLUTE';
    if (t.textAutoResize === 'WIDTH_AND_HEIGHT') n.textAutoResize = 'WIDTH_AND_HEIGHT';
    else { n.resize(Math.max(1, t.width), Math.max(1, t.height)); n.textAutoResize = t.textAutoResize === 'NONE' ? 'NONE' : 'HEIGHT'; }
    if (inAL && t.layoutPositioning !== 'ABSOLUTE') {
      n.layoutAlign = t.layoutAlign; n.layoutGrow = t.layoutGrow;
      try { n.layoutSizingHorizontal = t.layoutSizingHorizontal; } catch (e) {}
      try { n.layoutSizingVertical = t.layoutSizingVertical; } catch (e) {}
      if (t.rotation) n.rotation = t.rotation;
    } else n.relativeTransform = t.relativeTransform;
    if (!inAL || t.layoutPositioning === 'ABSOLUTE') n.constraints = t.constraints;
    map[t.id] = n.id;
    t.remove();
  }
  // unavailableStyles не пусто — в стилях уже стоят оригинальные шрифты: попросить дизайнера
  // вернуть замены на время сборки (references/colors.md, «Привязка цветов», шаг 4); skipped — нетронутые тексты
  return { map, count: texts.length, missingStyles: [...missing], unavailableStyles: [...unavailable], skipped };
}
