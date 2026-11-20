// Геометрический QA макета для use_figma / figma_execute (только чтение).
// Перед запуском заменить ROOT_ID на id корневого фрейма страницы/прототипа
// (из ссылки: node-id=6002-18 → '6002:18').
//
// Проверяет:
//  1) выход любых узлов за границы секций (дети root верхнего уровня), допуск 2px;
//  2) TEXT, обрезанный clipping-родителем (frame c clipsContent);
//  3) переполнение auto-layout фреймов с фиксированной осью
//     (Σ размеров детей + spacing + padding > размера фрейма);
//  4) попарные пересечения TEXT > 8px; узлы под общим повёрнутым предком
//     пропускаются — axis-aligned bbox повёрнутых фреймов даёт false-positive;
//  5) вырожденный TEXT шириной < 2px (признак схлопывания/переноса).
//
// Намеренные выпуски за край (обрезанные карточки веера, лого-подпись с bleed)
// перечислить в ALLOW_CLIP по именам слоёв. Имена слоёв прототипа — БЭМ
// (hero__title, cards__card-01), поэтому allow-list стабилен.
//
// Возвращает { issueCount, issues, checkedSections }. Цель: issueCount = 0.
// Это первичный слой проверки; vision-сверка скриншотов — вторичный слой.

const ROOT_ID = '1:98';
const ALLOW_CLIP = new Set([
  // 'footer__logo-signature',
  // 'cards__card-01', 'cards__card-04',
]);

const root = await figma.getNodeByIdAsync(ROOT_ID);
if (!root) throw new Error('Нет узла ' + ROOT_ID);

const issues = [];
const EPS = 2;

const underRotated = (n, stop) => {
  let p = n.parent;
  while (p && p !== stop) {
    if ('rotation' in p && p.rotation) return true;
    p = p.parent;
  }
  return false;
};

// Секции = дети root верхнего уровня (страница-прототип); если root сам контентный — [root]
const sections = ('children' in root && root.children.length && root.children.every(c => 'absoluteBoundingBox' in c))
  ? root.children
  : [root];

for (const sec of sections) {
  const sb = sec.absoluteBoundingBox;
  if (!sb) continue;
  const all = sec.findAll ? sec.findAll(() => true) : [];
  const texts = [];

  for (const d of all) {
    const b = d.absoluteBoundingBox;
    if (!b) continue;

    // 1) выход за границы секции
    const out = [
      b.x < sb.x - EPS ? 'L' : '',
      b.x + b.width > sb.x + sb.width + EPS ? 'R' : '',
      b.y < sb.y - EPS ? 'T' : '',
      b.y + b.height > sb.y + sb.height + EPS ? 'B' : '',
    ].filter(Boolean).join('');
    if (out && !ALLOW_CLIP.has(d.name)) {
      issues.push({ sec: sec.name, node: `${d.name} (${d.id})`, type: 'OUT:' + out,
        bbox: [Math.round(b.x - sb.x), Math.round(b.y - sb.y), Math.round(b.width), Math.round(b.height)],
        secWH: [Math.round(sb.width), Math.round(sb.height)] });
    }

    // 2) TEXT, обрезанный clipping-родителем
    if (d.type === 'TEXT' && d.parent && d.parent.type === 'FRAME' && d.parent.clipsContent
        && d.parent !== sec && !ALLOW_CLIP.has(d.name)) {
      const pb = d.parent.absoluteBoundingBox;
      if (b.x < pb.x - 1 || b.x + b.width > pb.x + pb.width + 1
          || b.y < pb.y - 1 || b.y + b.height > pb.y + pb.height + 1) {
        issues.push({ sec: sec.name, node: `${d.name} in ${d.parent.name}`, type: 'CLIPPED-IN-PARENT',
          text: d.characters.slice(0, 40) });
      }
    }

    // 5) вырожденный текст
    if (d.type === 'TEXT' && d.width < 2) {
      issues.push({ sec: sec.name, node: `${d.name} (${d.id})`, type: 'THIN-TEXT' });
    }
    if (d.type === 'TEXT') texts.push(d);

    // 3) переполнение auto-layout с фиксированной осью
    if ('layoutMode' in d && (d.layoutMode === 'VERTICAL' || d.layoutMode === 'HORIZONTAL') && d.children) {
      const vertical = d.layoutMode === 'VERTICAL';
      const fixed = vertical ? d.primaryAxisSizingMode === 'FIXED' : d.counterAxisSizingMode === 'FIXED';
      if (fixed && d.children.length) {
        const size = n => (vertical ? n.height : n.width);
        const pad = vertical
          ? d.paddingTop + d.paddingBottom
          : d.paddingLeft + d.paddingRight;
        const total = d.children.reduce((a, ch) => a + size(ch), 0)
          + d.itemSpacing * (d.children.length - 1) + pad;
        if (total > size(d) + 1) {
          issues.push({ sec: sec.name, node: `${d.name} (${d.id})`, type: 'AL-OVERFLOW',
            total: Math.round(total), frame: Math.round(size(d)), axis: d.layoutMode });
        }
      }
    }
  }

  // 4) попарные пересечения TEXT (без повёрнутых предков)
  for (let i = 0; i < texts.length; i++) {
    if (underRotated(texts[i], sec)) continue;
    for (let j = i + 1; j < texts.length; j++) {
      if (underRotated(texts[j], sec)) continue;
      const a = texts[i].absoluteBoundingBox, bb = texts[j].absoluteBoundingBox;
      if (!a || !bb) continue;
      const ox = Math.min(a.x + a.width, bb.x + bb.width) - Math.max(a.x, bb.x);
      const oy = Math.min(a.y + a.height, bb.y + bb.height) - Math.max(a.y, bb.y);
      if (ox > 8 && oy > 8) {
        issues.push({ sec: sec.name, type: 'TEXT-OVERLAP',
          a: `${texts[i].name}: ${texts[i].characters.slice(0, 24)}`,
          b: `${texts[j].name}: ${texts[j].characters.slice(0, 24)}`,
          ox: Math.round(ox), oy: Math.round(oy) });
      }
    }
  }
}

return { issueCount: issues.length, checkedSections: sections.length, issues };
