#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""canvas_cli.py — агентское ядро obs-canvas-clipper (фаза 2).

Прямая запись в .canvas через Syncthing-копию vault (без REST API).
Только stdlib; PIL используется опционально (если установлен) для измерения
картинок, иначе — встроенные парсеры заголовков PNG/JPEG/GIF/BMP/WebP/SVG.

Раскладка и константы ДОЛЖНЫ совпадать с extension/core.js (ТЗ §5,
«одно ядро — две обёртки»). Синхронность проверяет tests/skill_sync.test.js.

Команды:
  list                      все *.canvas vault'а (рекурсивно)
  create NAME               новый пустой canvas в КОРНЕ vault
  add SOURCE [--canvas REL | --new NAME] [--folder DIR] [--target-height PX]

SOURCE — http(s) URL или путь к локальному файлу.
Результат — одна строка JSON в stdout (для агента); человекочитаемое — в stderr.
Коды выхода: 0 ок; 2 аргументы; 3 canvas (нет/битый); 4 источник/сеть;
5 Syncthing прямо сейчас синхронизирует файл (повторить позже).
"""

import argparse
import hashlib
import json
import os
import re
import secrets
import struct
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

DEFAULT_VAULT = os.environ.get("OBSIDIAN_VAULT") or os.path.expanduser("~/Sync/ObsidianVault")

SKIP_DIRS = {".obsidian", ".trash", ".git", "node_modules"}

# --- константы раскладки: СИНХРОННО с extension/core.js ---------------------
ROW_WIDTH = 1600
GAP = 40
TARGET_HEIGHT = 300        # DEFAULTS.nodeHeight в core.js
FALLBACK_WIDTH = 640       # FALLBACK_SIZE в core.js
FALLBACK_HEIGHT = 480
# -----------------------------------------------------------------------------

MIN_SIZE = 64
MAX_BYTES = 40 * 1024 * 1024
UA = "Mozilla/5.0 (X11; Linux x86_64) obs-canvas-clipper/0.3"

EXT_BY_CT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/avif": "avif",
    "image/svg+xml": "svg",
    "image/bmp": "bmp",
}
KNOWN_EXT = {"png", "jpg", "jpeg", "webp", "gif", "avif", "svg", "bmp"}


class CliError(Exception):
    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


# --- имена и пути (конвенции vault: `--`, без `::`, NFC) ---------------------

def sanitize_name(name):
    s = unicodedata.normalize("NFC", str(name))
    s = s.replace("::", "--")
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "-", s)
    s = s.rstrip(". ")
    if not s or s in (".", ".."):
        raise CliError("некорректное имя: %r" % (name,), 2)
    return s


def sanitize_folder(folder):
    s = unicodedata.normalize("NFC", str(folder or "")).strip().strip("/")
    if not s:
        return ""
    parts = []
    for p in s.split("/"):
        p = p.replace("::", "--")
        p = re.sub(r'[\\:*?"<>|\x00-\x1f]', "-", p)
        p = p.rstrip(". ")
        if not p or p in (".", ".."):
            raise CliError("некорректный путь папки: %r" % (folder,), 2)
        parts.append(p)
    return "/".join(parts)


def resolve_in_vault(vault, rel):
    """rel → абсолютный путь внутри vault; выход за vault запрещён."""
    p = os.path.normpath(os.path.join(vault, rel))
    if p != vault and not p.startswith(vault + os.sep):
        raise CliError("путь вне vault: %r" % (rel,), 2)
    return p


def sha6(text):
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:6]


def timestamp_name(dt=None):
    dt = dt or datetime.now()
    return dt.strftime("%Y%m%d-%H%M%S")


def ext_from_ct(ct):
    if not ct:
        return None
    return EXT_BY_CT.get(ct.split(";")[0].strip().lower())


def ext_from_url(url):
    path = urllib.parse.urlparse(url).path
    m = re.search(r"\.([A-Za-z0-9]+)$", path)
    if not m:
        return None
    low = m.group(1).lower()
    if low == "jpeg":
        return "jpg"
    return low if low in KNOWN_EXT else None


def ext_from_magic(data):
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:2] == b"BM":
        return "bmp"
    if data[4:8] == b"ftyp":
        return "avif"
    if data.lstrip()[:200].lower().startswith(b"<?xml") or b"<svg" in data[:512]:
        return "svg"
    return None


# --- натуральные размеры (PIL опционально, иначе парсеры заголовков) ---------

def _pil_size(data):
    try:
        import io

        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(io.BytesIO(data)) as im:
            return im.size
    except Exception:
        return None


def _png_size(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    return None


def _jpeg_size(data):
    if data[:3] != b"\xff\xd8\xff":
        return None
    i = 2
    n = len(data)
    while i + 9 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        (seg_len,) = struct.unpack(">H", data[i + 2 : i + 4])
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            if i + 9 <= n:
                h, w = struct.unpack(">HH", data[i + 5 : i + 9])
                return w, h
            return None
        i += 2 + seg_len
    return None


def _gif_size(data):
    if data[:6] in (b"GIF87a", b"GIF89a"):
        w, h = struct.unpack("<HH", data[6:10])
        return w, h
    return None


def _bmp_size(data):
    if data[:2] == b"BM":
        w, h = struct.unpack("<ii", data[18:26])
        return w, abs(h)
    return None


def _webp_size(data):
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    fourcc = data[12:16]
    if fourcc == b"VP8X":
        w = 1 + (data[24] | (data[25] << 8) | (data[26] << 16))
        h = 1 + (data[27] | (data[28] << 8) | (data[29] << 16))
        return w, h
    if fourcc == b"VP8L":
        b0, b1, b2, b3 = data[21], data[22], data[23], data[24]
        w = 1 + (((b1 & 0x3F) << 8) | b0)
        h = 1 + (((b3 & 0x0F) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6))
        return w, h
    if fourcc == b"VP8 ":
        frame_tag = data[23] | (data[24] << 8) | (data[25] << 16)
        if frame_tag & 1:
            return None  # не ключевой кадр — не разберём без декодера
        if data[26:29] == b"\x9d\x01\x2a":
            w = (data[29] | (data[30] << 8)) & 0x3FFF
            h = (data[31] | (data[32] << 8)) & 0x3FFF
            return w, h
    return None


def _svg_size(data):
    try:
        text = data[:8192].decode("utf-8", "replace")
    except Exception:
        return None
    if "<svg" not in text.lower():
        return None

    def num(s):
        m = re.match(r"\s*([-+]?\d*\.?\d+)", s or "")
        return float(m.group(1)) if m else None

    tag_m = re.search(r"<svg[^>]*>", text, re.I | re.S)
    tag = tag_m.group(0) if tag_m else text
    w = num((re.search(r'\bwidth\s*=\s*"([^"]+)"', tag) or [None, None])[1])
    h = num((re.search(r'\bheight\s*=\s*"([^"]+)"', tag) or [None, None])[1])
    if w and h:
        return int(w), int(h)
    vb = re.search(r'viewBox\s*=\s*"([^"]+)"', tag)
    if vb:
        parts = vb.group(1).replace(",", " ").split()
        if len(parts) == 4:
            try:
                return int(float(parts[2])), int(float(parts[3]))
            except ValueError:
                return None
    return None


def image_size(data, ext=None):
    s = _pil_size(data)
    if s:
        return s
    parsers = {
        "png": _png_size,
        "jpg": _jpeg_size,
        "jpeg": _jpeg_size,
        "gif": _gif_size,
        "bmp": _bmp_size,
        "webp": _webp_size,
        "svg": _svg_size,
    }
    if ext and ext in parsers:
        s = parsers[ext](data)
        if s:
            return s
    for fn in (_png_size, _jpeg_size, _gif_size, _bmp_size, _webp_size):
        s = fn(data)
        if s:
            return s
    return None


# --- .canvas: parse / mutate / serialize / atomic write ----------------------

def parse_canvas(text):
    try:
        doc = json.loads(text)
    except Exception:
        raise CliError("целевой .canvas — невалидный JSON; ничего не пишем", 3)
    if not isinstance(doc, dict):
        raise CliError(".canvas: ожидался JSON-объект", 3)
    doc.setdefault("nodes", [])
    doc.setdefault("edges", [])
    if not isinstance(doc["nodes"], list) or not isinstance(doc["edges"], list):
        raise CliError(".canvas: nodes/edges — не массивы", 3)
    return doc


def serialize_canvas(doc):
    return json.dumps(doc, ensure_ascii=False, indent=2)


def atomic_write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=".occ-", suffix=".tmp", dir=os.path.dirname(path) or "."
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o644)  # конвенция sync-области проекта
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def syncthing_busy(vault, canvas_abs, img_dir_abs):
    """~syncthing~* рядом с целью = файл прямо сейчас синхронизируется."""
    dirs = {os.path.dirname(canvas_abs), img_dir_abs, vault}
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        try:
            for name in os.listdir(d):
                if name.startswith("~syncthing~"):
                    return name
        except OSError:
            pass
    return None


# --- раскладка (дословный порт findFreeSpot из extension/core.js) ------------

def scaled_size(nat_w, nat_h, target_h):
    h = min(nat_h, target_h)
    w = round(nat_w * (h / nat_h))
    return max(1, w), max(1, h)


def node_rects(doc):
    rects = []
    for n in doc.get("nodes") or []:
        if not isinstance(n, dict):
            continue
        vals = [n.get(k) for k in ("x", "y", "width", "height")]
        if all(isinstance(v, (int, float)) and v == v and v not in (float("inf"), float("-inf")) for v in vals):
            rects.append((n["x"], n["y"], n["width"], n["height"]))
    return rects


def _intersects(ax, ay, aw, ah, r):
    rx, ry, rw, rh = r
    return ax < rx + rw and ax + aw > rx and ay < ry + rh and ay + ah > ry


def find_free_spot(rects, w, h):
    if not rects:
        return 0, 0
    min_x = min(r[0] for r in rects)
    srt = sorted(rects, key=lambda r: r[1])
    rows = []
    for (rx, ry, rw, rh) in srt:
        if rows and ry < rows[-1]["bottom"]:
            rows[-1]["bottom"] = max(rows[-1]["bottom"], ry + rh)
            rows[-1]["right"] = max(rows[-1]["right"], rx + rw)
        else:
            rows.append({"top": ry, "bottom": ry + rh, "right": rx + rw})
    last = rows[-1]
    x = last["right"] + GAP
    y = last["top"]
    if x + w > min_x + ROW_WIDTH:
        x = min_x
        y = last["bottom"] + GAP
    guard = 0
    while guard < 100 and any(_intersects(x, y, w, h, r) for r in rects):
        guard += 1
        blockers = [r for r in rects if _intersects(x, y, w, h, r)]
        x = min_x
        y = max(r[1] + r[3] for r in blockers) + GAP
    if any(_intersects(x, y, w, h, r) for r in rects):
        raise CliError("не найдено свободное место на холсте", 3)
    return x, y


def node_id(taken):
    for _ in range(64):
        cand = secrets.token_hex(4)
        if cand not in taken:
            return cand
    raise CliError("не удалось сгенерировать уникальный id ноды", 3)


# --- источник картинки --------------------------------------------------------

def read_source(source):
    """→ (data, ext, source_id). source — URL или локальный путь."""
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read(MAX_BYTES + 1)
                ct = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            raise CliError("не удалось скачать картинку: HTTP %s (%s)" % (e.code, source), 4)
        except Exception as e:
            raise CliError("не удалось скачать картинку (%s): %s" % (source, e), 4)
        if len(data) > MAX_BYTES:
            raise CliError("картинка больше %d МБ — не берём" % (MAX_BYTES // (1024 * 1024)), 4)
        if not data:
            raise CliError("пустой ответ от %s" % source, 4)
        ext = ext_from_ct(ct) or ext_from_url(source) or ext_from_magic(data)
        return data, ext, source
    path = os.path.abspath(os.path.expanduser(source))
    if not os.path.isfile(path):
        raise CliError("локальный файл не найден: %s" % path, 4)
    if os.path.getsize(path) > MAX_BYTES:
        raise CliError("файл больше %d МБ — не берём" % (MAX_BYTES // (1024 * 1024)), 4)
    with open(path, "rb") as f:
        data = f.read()
    stem, dot_ext = os.path.splitext(os.path.basename(path))
    ext = dot_ext[1:].lower() if dot_ext else None
    if ext == "jpeg":
        ext = "jpg"
    if ext not in KNOWN_EXT:
        ext = ext_from_magic(data)
    return data, ext, "%s:%d" % (path, len(data))


# --- команды ------------------------------------------------------------------

def cmd_list(args):
    vault = os.path.abspath(args.vault)
    if not os.path.isdir(vault):
        raise CliError("vault не найден: %s" % vault, 2)
    canvases = []
    for root, dirs, files in os.walk(vault):
        rel_root = os.path.relpath(root, vault)
        depth = 0 if rel_root == "." else rel_root.count(os.sep) + 1
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        if depth >= args.max_depth:
            dirs[:] = []
        for f in files:
            if f.lower().endswith(".canvas"):
                rel = f if rel_root == "." else os.path.join(rel_root, f).replace(os.sep, "/")
                canvases.append(rel)
    canvases.sort()
    return {"ok": True, "canvases": canvases}


def cmd_create(args):
    vault = os.path.abspath(args.vault)
    if not os.path.isdir(vault):
        raise CliError("vault не найден: %s" % vault, 2)
    base = sanitize_name(re.sub(r"\.canvas$", "", args.name, flags=re.I))
    rel = base + ".canvas"
    path = resolve_in_vault(vault, rel)
    if os.path.exists(path):
        raise CliError('canvas "%s" уже существует — выберите другое имя' % rel, 3)
    busy = syncthing_busy(vault, path, vault)
    if busy:
        raise CliError("Syncthing синхронизирует %s — повторите позже" % busy, 5)
    atomic_write(path, serialize_canvas({"nodes": [], "edges": []}))
    return {"ok": True, "canvas": rel}


def cmd_add(args):
    vault = os.path.abspath(args.vault)
    if not os.path.isdir(vault):
        raise CliError("vault не найден: %s" % vault, 2)
    if bool(args.canvas) == bool(args.new):
        raise CliError("нужно ровно одно: --canvas <путь> или --new <имя>", 2)

    folder_rel = sanitize_folder(args.folder)
    folder_abs = resolve_in_vault(vault, folder_rel) if folder_rel else vault

    # 1) источник
    data, ext, source_id = read_source(args.source)
    if not ext:
        raise CliError(
            "не удалось определить формат картинки (для экзотики поставьте Pillow: pip install pillow)", 4
        )

    # 2) цель: canvas
    if args.new:
        base = sanitize_name(re.sub(r"\.canvas$", "", args.new, flags=re.I))
        canvas_rel = base + ".canvas"
        canvas_abs = resolve_in_vault(vault, canvas_rel)
        if os.path.exists(canvas_abs):
            raise CliError('canvas "%s" уже существует' % canvas_rel, 3)
        busy = syncthing_busy(vault, canvas_abs, folder_abs)
        if busy:
            raise CliError("Syncthing синхронизирует %s — повторите позже" % busy, 5)
        atomic_write(canvas_abs, serialize_canvas({"nodes": [], "edges": []}))
    else:
        canvas_rel = args.canvas.replace(os.sep, "/").lstrip("/")
        if not canvas_rel.lower().endswith(".canvas"):
            raise CliError("цель должна быть .canvas: %r" % args.canvas, 2)
        canvas_abs = resolve_in_vault(vault, canvas_rel)
        if not os.path.isfile(canvas_abs):
            raise CliError("canvas не найден: %s (list — все холсты)" % canvas_rel, 3)

    # 3) имя и запись картинки
    stamp = timestamp_name()
    name = "clip--%s--%s.%s" % (stamp, sha6(source_id), ext)
    img_rel = (folder_rel + "/" + name) if folder_rel else name
    img_abs = resolve_in_vault(vault, img_rel)
    if os.path.exists(img_abs):
        name = "clip--%s--%s-%d.%s" % (stamp, sha6(source_id), os.getpid(), ext)
        img_rel = (folder_rel + "/" + name) if folder_rel else name
        img_abs = resolve_in_vault(vault, img_rel)
    os.makedirs(os.path.dirname(img_abs), exist_ok=True)
    atomic_write(img_abs, data)

    # 4) размеры и раскладка
    nat = image_size(data, ext)
    if nat:
        w, h = scaled_size(nat[0], nat[1], args.target_height)
    else:
        w, h = FALLBACK_WIDTH, FALLBACK_HEIGHT

    # 5) вставка ноды с verify-after-write и повторами (диск общий с Obsidian/Syncthing)
    node_out = None
    attempts = 0
    last_err = None
    for attempt in range(1, args.max_attempts + 1):
        attempts = attempt
        busy = syncthing_busy(vault, canvas_abs, folder_abs)
        if busy:
            last_err = CliError("Syncthing синхронизирует %s" % busy, 5)
            if attempt < args.max_attempts:
                time.sleep(0.7)
                continue
            break
        try:
            with open(canvas_abs, "r", encoding="utf-8") as f:
                doc = parse_canvas(f.read())
        except CliError as e:
            raise e
        except Exception as e:
            last_err = CliError("не читается %s: %s" % (canvas_rel, e), 3)
            if attempt < args.max_attempts:
                time.sleep(0.7)
                continue
            break
        taken = {n.get("id") for n in doc["nodes"] if isinstance(n, dict)}
        x, y = find_free_spot(node_rects(doc), w, h)
        node = {
            "id": node_id(taken),
            "type": "file",
            "file": img_rel,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
        }
        doc["nodes"].append(node)
        try:
            atomic_write(canvas_abs, serialize_canvas(doc))
        except Exception as e:
            last_err = CliError("запись %s не удалась: %s" % (canvas_rel, e), 3)
            if attempt < args.max_attempts:
                time.sleep(0.7)
                continue
            break
        try:
            with open(canvas_abs, "r", encoding="utf-8") as f:
                check = parse_canvas(f.read())
            if any(n.get("id") == node["id"] for n in check["nodes"]):
                node_out = node
                break
            last_err = CliError("вставленная нода исчезла (файл правится параллельно)", 3)
        except Exception as e:
            last_err = CliError("verify не удался: %s" % e, 3)
        if attempt < args.max_attempts:
            time.sleep(0.7)

    if node_out is None:
        raise CliError(
            "не удалось вставить ноду за %d попытки (%s). Картинка уже лежит: %s — "
            "повторите add, она не дублируется" % (args.max_attempts, last_err, img_rel),
            getattr(last_err, "code", 3),
        )

    return {
        "ok": True,
        "canvas": canvas_rel,
        "image": img_rel,
        "node": node_out,
        "natural": {"width": nat[0], "height": nat[1]} if nat else None,
        "attempts": attempts,
        "bytes": len(data),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="canvas_cli",
        description="Агентская запись картинок на .canvas vault (Syncthing-путь).",
    )
    ap.add_argument("--vault", default=DEFAULT_VAULT, help="корень vault (дефолт %s)" % DEFAULT_VAULT)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="все *.canvas vault'а")
    p_list.add_argument("--max-depth", type=int, default=12)

    p_create = sub.add_parser("create", help="новый пустой canvas в корне vault")
    p_create.add_argument("name")

    p_add = sub.add_parser("add", help="картинка (URL или файл) → нода на canvas")
    p_add.add_argument("source", help="http(s) URL или путь к локальному файлу")
    tgt = p_add.add_mutually_exclusive_group(required=True)
    tgt.add_argument("--canvas", help="vault-relative путь .canvas")
    tgt.add_argument("--new", help="создать canvas с этим именем в корне vault")
    p_add.add_argument("--folder", default="Canvas Inbox", help="папка картинок (дефолт 'Canvas Inbox', '' = корень)")
    p_add.add_argument("--target-height", type=int, default=TARGET_HEIGHT)
    p_add.add_argument("--max-attempts", type=int, default=3)

    args = ap.parse_args(argv)
    try:
        if args.cmd == "list":
            result = cmd_list(args)
        elif args.cmd == "create":
            result = cmd_create(args)
        else:
            result = cmd_add(args)
    except CliError as e:
        print("ошибка: %s" % e, file=sys.stderr)
        print(json.dumps({"ok": False, "error": str(e), "code": e.code}, ensure_ascii=False))
        return e.code
    print(json.dumps(result, ensure_ascii=False))
    if not os.environ.get("OCC_QUIET"):
        if result.get("image"):
            print(
                "✓ %s → %s (нода %s в %s)"
                % (result["image"], result["canvas"], result["node"]["id"], result["canvas"]),
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
