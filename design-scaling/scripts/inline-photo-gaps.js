// Мини-фото внутри строки текста («Лид с врезками», приём фрэнки «мини-фото во фразе») — для use_figma / figma_execute.
// В Figma нельзя вставить картинку в текст. Приём концепций: в текст вставляют пробелы
// («окно»), а фото кладут поверх окна абсолютно. Позицию окна не угадывать — эта функция
// её измеряет: подбирает число пробелов под ширину фото, находит строку и x начала окна,
// переносит окно на следующее слово, если оно попало на перенос строки.
//
// Использование: вставить в скрипт use_figma / figma_execute и вызвать
//   const res = await inlinePhotoGaps({
//     parent,                 // фрейм без auto layout (или с clipsContent = false), куда класть текст и фото
//     text: 'The studio is a new contemporary art gallery that …',  // дословно из текстов страницы
//     style: 'Лид / L', role: 'текст/основной',
//     width: 1820,            // ширина текстовой колонки
//     anchors: ['gallery', 'experiments,'],  // слово, ПОСЛЕ которого окно; по одному на фото, в порядке текста
//     photo: { w: 108, h: 84, role: 'фото/подложка', name: 'Фото / мини' },
//     muted: { role: 'текст/второстепенный', phrases: ['contemporary art gallery'] },  // необязательно
//   })
//   → { textId, photos: [{ id, x, y }], spaces, moved: [...], failed: [...] }
// DRY_RUN = true (умолчание): постоянных узлов не создаёт — замерные клоны (tmp, wm)
// удаляются, как и раньше; финальные текст и фото-фреймы не создаются, parent не
// ресайзится; в photos — планируемые x/y (id: null), textId: null, plannedText — текст
// с вставленными окнами; отсутствующие роли — в noRoles (в реальном прогоне это бросок).
// Поставить false, чтобы писать по-настоящему.
// Затем — image-prompt.js по photos[].id. В отчёт: «в текст вставлены пробелы под врезки» —
// слова не менялись, но символы текста отличаются от источника.
// Межстрочный стиля — в процентах или px; AUTO не поддержан (вернёт ошибку).

// true — замер и отчёт без постоянной записи: финальные узлы не создаются.
// Поставить false, чтобы вставлять текст и врезки по-настоящему.
const DRY_RUN = true;

async function inlinePhotoGaps(o) {
  const st = (await figma.getLocalTextStylesAsync()).find(s => s.name === o.style);
  if (!st) throw new Error('Нет текстового стиля ' + o.style);
  await figma.loadFontAsync(st.fontName);
  const vars = await figma.variables.getLocalVariablesAsync('COLOR');
  const role = n => { const v = vars.find(x => x.name === n); if (!v) throw new Error('Нет роли ' + n); return v; };
  // в заливку кладём фактическое значение роли: с заглушкой-серым Figma иногда так и рисует
  const paint = async n => { const v = role(n); const col = await figma.variables.getVariableCollectionByIdAsync(v.variableCollectionId);
    let val = v.valuesByMode[col.defaultModeId];
    for (let d = 0; val && val.type === 'VARIABLE_ALIAS' && d < 5; d++) { const t = await figma.variables.getVariableByIdAsync(val.id); const c = await figma.variables.getVariableCollectionByIdAsync(t.variableCollectionId); val = t.valuesByMode[c.defaultModeId]; }
    const color = val && 'r' in val ? { r: val.r, g: val.g, b: val.b } : { r: .5, g: .5, b: .5 };
    return figma.variables.setBoundVariableForPaint({ type: 'SOLID', color, opacity: val && val.a !== undefined ? val.a : 1 }, 'color', v); };
  const LH = st.lineHeight.unit === 'PERCENT' ? st.fontSize * st.lineHeight.value / 100 : st.lineHeight.unit === 'PIXELS' ? st.lineHeight.value : null;
  if (!LH) throw new Error('Межстрочный стиля AUTO — задать в процентах или px');

  const mk = () => { const t = figma.createText(); o.parent.appendChild(t); t.textStyleId = st.id; t.characters = 'a'; return t; };
  const tmp = mk(); tmp.resize(o.width, 10); tmp.textAutoResize = 'HEIGHT';
  const wm = mk(); wm.textAutoResize = 'WIDTH_AND_HEIGHT';
  const lines = s => { tmp.characters = s.length ? s : 'a'; return Math.round(tmp.height / LH); };
  const widthOf = s => { wm.characters = s || 'a'; return s ? wm.width : 0; };
  const sp = widthOf('a a') - widthOf('aa');
  const k = Math.ceil((o.photo.w + 2 * sp) / sp);

  // Меряем всегда префикс до КОНЦА слова: обрывок слова («exp», «t») может влезть в строку,
  // в которую целое слово уже не влезает, — и начало строки или перенос найдутся неверно.
  const endOf = (S, i) => { const j = S.indexOf(' ', i); return j < 0 ? S.length : j; };
  // x окна на строке L: начало строки — первое слово, чей префикс-до-конца-слова уже на строке L
  const xOf = (S, gi, L) => {
    const starts = [];
    for (let i = 0; i < gi; i++) if (S[i] !== ' ' && (i === 0 || S[i - 1] === ' ')) starts.push(i);
    let lo = 0, hi = starts.length - 1;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (lines(S.slice(0, endOf(S, starts[mid]))) >= L) hi = mid; else lo = mid + 1; }
    return Math.round(widthOf(S.slice(starts[lo], gi)) + sp);
  };
  let F = o.text; const photos = [], moved = [], failed = [];
  for (const anchor of o.anchors) {
    let gi = F.indexOf(anchor); if (gi < 0) { failed.push(anchor + ': нет в тексте'); continue; }
    gi += anchor.length; let placed = false;
    for (let tries = 0; tries < 8 && !placed && gi > 0; tries++) {
      const cand = F.slice(0, gi) + ' '.repeat(k) + F.slice(gi);
      const L = lines(cand.slice(0, gi));
      // окно и следующее слово целиком на той же строке, и фото не вылезает за колонку
      // после окна стоит исходный пробел (cand[gi + k]), слово начинается с gi + k + 1
      const sameLine = L === lines(cand.slice(0, endOf(cand, gi + k + 1)));
      const x = sameLine ? xOf(cand, gi, L) : Infinity;
      if (sameLine && x + o.photo.w <= o.width) {
        F = cand; placed = true;
        photos.push({ x, y: Math.round((L - 1) * LH + (LH - o.photo.h) / 2) });
        if (tries) moved.push(anchor + ' → +' + tries + ' слов');
      } else gi = F.indexOf(' ', gi + 1);
    }
    if (!placed) failed.push(anchor + ': окно всё время попадает на перенос');
  }
  tmp.remove(); wm.remove();

  // dry-run: постоянных узлов не создаём. Проверяем то, на чём упал бы реальный прогон:
  // наличие ролей (paint бросил бы «Нет роли») и фразы muted; отдаём план раскладки
  if (DRY_RUN) {
    const noRoles = [];
    for (const rn of [o.role, o.photo.role, o.muted && o.muted.role]) if (rn && !vars.find(x => x.name === rn)) noRoles.push(rn);
    if (o.muted) for (const ph of o.muted.phrases) if (F.indexOf(ph) < 0) failed.push('muted: нет фразы «' + ph + '»');
    return { textId: null, photos: photos.map(p => ({ id: null, x: p.x, y: p.y })), spaces: k, moved, failed, noRoles,
      dryRun: true, plannedText: F };
  }
  const t = figma.createText(); o.parent.appendChild(t); t.textStyleId = st.id; t.characters = F;
  t.resize(o.width, 10); t.textAutoResize = 'HEIGHT'; t.x = 0; t.y = 0; t.fills = [await paint(o.role)];
  if (o.muted) for (const ph of o.muted.phrases) { const i = F.indexOf(ph); if (i >= 0) t.setRangeFills(i, i + ph.length, [await paint(o.muted.role)]); else failed.push('muted: нет фразы «' + ph + '»'); }
  const out = [];
  for (let i = 0; i < photos.length; i++) {
    const f = figma.createFrame(); o.parent.appendChild(f); f.name = `${o.photo.name} ${i + 1}`;
    f.resize(o.photo.w, o.photo.h); f.fills = [await paint(o.photo.role)];
    if ('layoutMode' in o.parent && o.parent.layoutMode !== 'NONE') f.layoutPositioning = 'ABSOLUTE'; // до x/y
    f.x = photos[i].x; f.y = photos[i].y;
    out.push({ id: f.id, ...photos[i] });
  }
  if ('layoutMode' in o.parent && o.parent.layoutMode === 'NONE') o.parent.resize(o.width, t.height);
  // проверить скриншотом: фото стоят в окнах, не на словах. Сдвиг на запятую — увеличить anchors на 1 символ
  return { textId: t.id, photos: out, spaces: k, moved, failed };
}
