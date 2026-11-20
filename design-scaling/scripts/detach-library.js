// Отвязывает клон концепции от внешней библиотеки — для use_figma.
// Когда нужен: концепция собрана на стилях и компонентах чужой библиотеки (color-audit.js
// вернул большой `styled`, в инвентаре инстансы с remote = true), и дизайнер согласился
// заменить их локальными ролями и стилями (references/colors.md, «Концепция на библиотеке»).
// Концепцию не трогать: функцию вызывать только на клонах (UI-kit, страницы).
//
// Что делает с узлом и всем его содержимым:
//  1. Отсоединяет каждый инстанс, включая вложенные (detachInstance до последнего).
//  2. Текст: сегмент на библиотечном стиле → локальный стиль по REMOTE_TO_LOCAL (имя
//     библиотечного стиля → имя локального); сегмент без стиля → STYLE_KEY по начертанию,
//     размеру и регистру. Регистр (UPPER, TITLE) хранится в стиле — локальный стиль должен
//     быть копией библиотечного со всеми свойствами, иначе пропадёт CAPS.
//  3. Снимает цветовые стили заливок, обводок и сегментов текста. Цвет остаётся «сырым» —
//     сразу после вызова запустить bind-colors.js по тому же узлу.
// Годится и для клона без библиотеки: тогда он только переведёт тексты без стиля по STYLE_KEY.
// Шрифты недоступны — тексты на них пропускает (fontBlocked), инстансы и стили остальных
// узлов всё равно отвязывает; после него по тому же узлу — restyle-texts.js.
//
// Использование: вставить в скрипт use_figma, заполнить REMOTE_TO_LOCAL и вызвать
//   const node = await detachLibrary(clone)   // инстанс вернётся фреймом — брать результат
//   return detachLibrary.report
// Локальные стили создать заранее (этап А, шаг 6): копировать fontName, fontSize, lineHeight,
// letterSpacing, textCase, textDecoration, paragraphSpacing с библиотечного стиля.

const REMOTE_TO_LOCAL = {
  // 'Заголовок 2': 'Заголовок / L',
};
// Для текстов без стиля. Подстроить под шкалу из дизайн-правила.md.
const STYLE_KEY = (style, size, textCase, lineHeightPct) => {
  const bold = /Semi|Bold/i.test(style), italic = /Italic/i.test(style);
  if (size >= 240) return italic ? 'Display / XL курсив' : 'Display / XL';
  if (size >= 65) return lineHeightPct > 110 ? 'Лид / L' : 'Заголовок / L';
  if (size >= 50) return 'Заголовок / M';
  if (size >= 23) return bold ? (textCase === 'UPPER' ? 'Заголовок / S CAPS' : 'Заголовок / S') : 'Поле / L';
  if (size >= 17) return bold ? 'Навигация / CAPS' : 'Кнопка / CAPS';
  return textCase === 'UPPER' ? 'Текст / S CAPS' : 'Текст / S';
};

async function detachLibrary(node) {
  const local = await figma.getLocalTextStylesAsync();
  const norm = s => s.replace(/\s*\/\s*/g, '/').trim();
  const byName = Object.fromEntries(local.map(s => [norm(s.name), s]));
  const localIds = new Set(local.map(s => s.id));
  for (const s of local) await figma.loadFontAsync(s.fontName);
  const rep = detachLibrary.report = { detached: 0, restyled: 0, byKey: [], stylesCleared: 0, missingStyles: [], unmapped: [], caseChanged: [], fontBlocked: [] };
  const cache = {};

  if (node.type === 'INSTANCE') { node = node.detachInstance(); rep.detached++; }
  if ('children' in node) { let i; while ((i = node.findOne(n => n.type === 'INSTANCE'))) { i.detachInstance(); rep.detached++; } }
  const all = 'children' in node ? [node, ...node.findAll(() => true)] : [node];

  for (const n of all) {
    if (n.type === 'TEXT') {
      const segs = n.getStyledTextSegments(['fontName', 'fontSize', 'textCase', 'lineHeight', 'textStyleId', 'fillStyleId']);
      // шрифт недоступен — текст не трогать: его пересоздаст restyle-texts.js (он же снимет цветовой стиль)
      let blocked = false;
      for (const s of segs) { try { await figma.loadFontAsync(s.fontName); } catch (e) { blocked = true; } }
      if (blocked) { if (rep.fontBlocked.length < 30) rep.fontBlocked.push(`${n.name.slice(0, 24)} #${n.id}`); continue; }
      for (const s of segs) {
        let target = null;
        if (s.textStyleId && !localIds.has(s.textStyleId)) {
          if (!(s.textStyleId in cache)) { const st = await figma.getStyleByIdAsync(s.textStyleId); cache[s.textStyleId] = st ? st.name : null; }
          const remoteName = cache[s.textStyleId];
          target = REMOTE_TO_LOCAL[remoteName] || (byName[norm(remoteName || '')] ? remoteName : null);
          if (!target) rep.unmapped.push(`${remoteName} — ${n.name.slice(0, 24)} #${n.id}`);
        }
        if (!target && !(s.textStyleId && localIds.has(s.textStyleId))) {
          const lh = s.lineHeight.unit === 'PERCENT' ? s.lineHeight.value : 100;
          target = STYLE_KEY(s.fontName.style, s.fontSize, s.textCase, lh);
          if (rep.byKey.length < 30) rep.byKey.push(`${n.name.slice(0, 20)} ${s.fontName.style} ${Math.round(s.fontSize)} ${s.textCase} → ${target}`);
        }
        if (target) {
          const st = byName[norm(target)];
          if (!st) { if (!rep.missingStyles.includes(target)) rep.missingStyles.push(target); }
          else {
            await n.setRangeTextStyleIdAsync(s.start, s.end, st.id); rep.restyled++;
            // регистр берётся из стиля: сегмент был в другом регистре — показать, не чинить молча
            if (st.textCase !== s.textCase && rep.caseChanged.length < 30) rep.caseChanged.push(`«${n.characters.slice(s.start, s.end).slice(0, 20)}» ${s.textCase} → ${st.textCase} (${st.name}) #${n.id}`);
          }
        }
        if (s.fillStyleId) { await n.setRangeFillStyleIdAsync(s.start, s.end, ''); rep.stylesCleared++; }
      }
    } else if ('fillStyleId' in n && typeof n.fillStyleId === 'string' && n.fillStyleId) { await n.setFillStyleIdAsync(''); rep.stylesCleared++; }
    if ('strokeStyleId' in n && typeof n.strokeStyleId === 'string' && n.strokeStyleId) { await n.setStrokeStyleIdAsync(''); rep.stylesCleared++; }
    if ('effectStyleId' in n && typeof n.effectStyleId === 'string' && n.effectStyleId) { await n.setEffectStyleIdAsync(''); rep.stylesCleared++; }
  }
  // missingStyles / unmapped не пусты — завести недостающие локальные стили или дописать
  // REMOTE_TO_LOCAL и запустить снова (функция идемпотентна для уже локальных стилей).
  // caseChanged не пуст — текст сменил регистр (в концепции LOWER, у стиля TITLE): завести
  // стиль-вариант с нужным регистром или вынести в «Разнобой».
  return node;
}
