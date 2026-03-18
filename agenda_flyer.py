"""
agenda_flyer.py  v8 — Story Mobile First
- Canvas dinámico calculado según eventos
- Flood-fill background removal (negro, blanco, gris — cualquier fondo)
- 2 columnas altura variable
- Fuentes grandes legibles en mobile
- Cursiva en título y headers de día
"""
def _ensure_fonts():
    """Descarga fuentes si no existen localmente."""
    import urllib.request, os
    os.makedirs("fonts", exist_ok=True)
    
    URLS = {
        "fonts/Bold.ttf":       "https://github.com/google/fonts/raw/refs/heads/main/ofl/barlowcondensed/BarlowCondensed-Bold.ttf",
        "fonts/BoldItalic.ttf": "https://github.com/google/fonts/raw/refs/heads/main/ofl/barlowcondensed/BarlowCondensed-BoldItalic.ttf",
        "fonts/Regular.ttf":    "https://github.com/google/fonts/raw/refs/heads/main/ofl/barlowcondensed/BarlowCondensed-Regular.ttf",
        "fonts/Italic.ttf":     "https://github.com/google/fonts/raw/refs/heads/main/ofl/barlowcondensed/BarlowCondensed-Italic.ttf",
        "fonts/Serif.ttf":      "https://github.com/google/fonts/raw/refs/heads/main/ofl/lora/Lora%5Bwght%5D.ttf",
        "fonts/SerifBold.ttf":  "https://github.com/google/fonts/raw/refs/heads/main/ofl/lora/Lora%5Bwght%5D.ttf",
    }
    for path, url in URLS.items():
        if not Path(path).exists():
            try:
                urllib.request.urlretrieve(url, path)
                print(f"  [fonts] descargado {path}")
            except Exception as e:
                print(f"  [fonts] no se pudo descargar {path}: {e}")

_ensure_fonts()  # llamar al importar
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from pathlib import Path
from datetime import date, timedelta
from collections import deque
from scipy import ndimage

_IMG_CACHE: dict = {}  # cache de logos procesados

W, H = 1280, 2280  # H se recalcula dinámicamente en generar_agenda

C = {
    "bg":        (10, 10, 16),
    "card":      (22, 22, 34),
    "border":    (42, 42, 60),
    "accent":    (91, 157, 213),
    "text_hi":   (242, 237, 225),
    "text_mid":  (185, 178, 165),
    "text_lo":   (110, 105, 98),
    "white":     (255, 255, 255),
    "footer_bg": (18, 14, 28),
}

TIPO_COLOR = {
    "altered":   ( 80, 160, 220),
    "warhammer": (190,  50,  50),
    "pokemon":   (240, 200,  40),
    "yugioh":    (200, 150,  30),
    "dnd":       (100, 155, 215),
    "magic":     (155,  90, 215),
    "tcg":       (220, 105,  35),
    "bingo":     ( 55, 190, 110),
    "pintura":   (175,  75, 195),
    "mesa":      ( 55, 175, 195),
    "virus":     ( 90, 200,  80),
    "default":   (130, 130, 150),
}

# ── Métricas globales ─────────────────────────────────────────────────────────
ICON_SZ  = 112   # icono sobre el evento
LH_HORA  = 36    # line-height hora  (font 26)
LH_EVM   = 44    # line-height nombre múltiple (font 36)
LH_EV1   = 50    # line-height nombre único (font 40)
LH_DESC  = 32    # line-height descripción (font 24)
SEP_H    = 18    # separador entre eventos
HCARD    = 66    # altura header del día
PAD_TOP  = 14    # padding tras el header
GPAD     = 16    # padding lateral del grid
CGAP     = 14    # gap entre columnas
RGAP     = 14    # gap entre tarjetas


# ── Resolución de fuentes cross-platform ─────────────────────────────────────

def _resolver_fuentes() -> dict:
    """
    Busca fuentes en este orden de prioridad:
      1. Carpeta ./fonts/ local (incluida en el repo) — CONSISTENTE en todos los OS
      2. Fuentes del sistema (Windows / macOS / Linux)
      3. PIL default como último recurso

    Para garantizar consistencia visual, descarga estas fuentes y ponlas en ./fonts/:
      bold        → fonts/Bold.ttf        (ej: Barlow-Bold.ttf, Oswald-Bold.ttf)
      bold_i      → fonts/BoldItalic.ttf
      regular     → fonts/Regular.ttf
      regular_i   → fonts/Italic.ttf
      serif       → fonts/Serif.ttf       (ej: Lora-Regular.ttf)
      serbold     → fonts/SerifBold.ttf

    Fuentes recomendadas (Google Fonts, licencia OFL):
      Sans: Barlow Condensed  https://fonts.google.com/specimen/Barlow+Condensed
      Serif: Lora             https://fonts.google.com/specimen/Lora
    """
    import platform, glob as _glob

    system = platform.system()

    # ── 1. Fuentes locales en ./fonts/ (máxima prioridad) ─────────────────────
    LOCAL = {
        "bold":     ["fonts/Bold.ttf", "fonts/BoldItalic.ttf",
                     "fonts/Barlow_Condensed/BarlowCondensed-Bold.ttf",
                     "fonts/Oswald-Bold.ttf"],
        "bold_i":   ["fonts/BoldItalic.ttf",
                     "fonts/Barlow_Condensed/BarlowCondensed-BoldItalic.ttf",
                     "fonts/Oswald-Bold.ttf"],
        "regular":  ["fonts/Regular.ttf",
                     "fonts/Barlow_Condensed/BarlowCondensed-Regular.ttf",
                     "fonts/Oswald-Regular.ttf"],
        "regular_i":["fonts/Italic.ttf",
                     "fonts/Barlow_Condensed/BarlowCondensed-Italic.ttf"],
        "serif":    ["fonts/Serif.ttf", "fonts/Lora/Lora-Regular.ttf"],
        "serbold":  ["fonts/SerifBold.ttf", "fonts/Lora/Lora-Bold.ttf"],
    }

    # ── 2. Fuentes del sistema ─────────────────────────────────────────────────
    SYSTEM = {
        "Windows": {
            "bold":     ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/calibrib.ttf"],
            "bold_i":   ["C:/Windows/Fonts/arialbi.ttf", "C:/Windows/Fonts/calibriz.ttf"],
            "regular":  ["C:/Windows/Fonts/arial.ttf",   "C:/Windows/Fonts/calibri.ttf"],
            "regular_i":["C:/Windows/Fonts/ariali.ttf",  "C:/Windows/Fonts/calibrii.ttf"],
            "serif":    ["C:/Windows/Fonts/georgia.ttf",  "C:/Windows/Fonts/times.ttf"],
            "serbold":  ["C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/timesbd.ttf"],
        },
        "Darwin": {
            "bold":     ["/Library/Fonts/Arial Bold.ttf",
                         "/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
            "bold_i":   ["/Library/Fonts/Arial Bold Italic.ttf",
                         "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf"],
            "regular":  ["/Library/Fonts/Arial.ttf",
                         "/System/Library/Fonts/Supplemental/Arial.ttf"],
            "regular_i":["/Library/Fonts/Arial Italic.ttf",
                         "/System/Library/Fonts/Supplemental/Arial Italic.ttf"],
            "serif":    ["/Library/Fonts/Georgia.ttf",
                         "/System/Library/Fonts/Supplemental/Georgia.ttf"],
            "serbold":  ["/Library/Fonts/Georgia Bold.ttf",
                         "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"],
        },
        "Linux": {
            "bold":     ["/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
                         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"],
            "bold_i":   ["/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-BoldOblique.ttf",
                         "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf"],
            "regular":  ["/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
                         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"],
            "regular_i":["/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Oblique.ttf",
                         "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"],
            "serif":    ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
                         "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"],
            "serbold":  ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                         "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"],
        },
    }

    resolved = {}
    sys_pool = SYSTEM.get(system, SYSTEM["Linux"])

    for role in ["bold", "bold_i", "regular", "regular_i", "serif", "serbold"]:
        found = None

        # Primero: local
        for path in LOCAL.get(role, []):
            if Path(path).exists():
                found = path
                break

        # Segundo: sistema
        if not found:
            for path in sys_pool.get(role, []):
                if Path(path).exists():
                    found = path
                    break

        # Tercero: glob del sistema
        if not found:
            pat = {"Windows": "C:/Windows/Fonts/*.ttf",
                   "Darwin":  "/Library/Fonts/*.ttf",
                   "Linux":   "/usr/share/fonts/**/*.ttf"}.get(system, "/usr/share/fonts/**/*.ttf")
            kw  = {"bold": "bold", "bold_i": "oblique", "regular": "regular",
                   "regular_i": "oblique", "serif": "serif", "serbold": "serif"}[role]
            hits = _glob.glob(pat, recursive=True)
            matches = [f for f in hits if kw in Path(f).name.lower()]
            if matches:
                found = matches[0]

        resolved[role] = found

    # Indicar fuente de cada rol
    print(f"[agenda_flyer] OS: {system}")
    for k, v in resolved.items():
        src = "LOCAL" if v and v.startswith("fonts/") else "SYSTEM"
        print(f"  {k:10s} [{src}] -> {v or 'PIL default'}")
    return resolved


FONT = _resolver_fuentes()


def fnt(key, size):
    path = FONT.get(key)
    return ImageFont.truetype(path, size) if path else ImageFont.load_default()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ev_color(nombre):
    n = nombre.lower()
    if "altered"   in n:                                  return TIPO_COLOR["altered"]
    if "warhammer" in n or "40k"    in n:                 return TIPO_COLOR["warhammer"]
    if "pokemon"   in n or "pokémon" in n:                return TIPO_COLOR["pokemon"]
    if "yu-gi"     in n or "yugioh" in n or "yu gi" in n: return TIPO_COLOR["yugioh"]
    if "calabozo"  in n or "d&d"    in n:                 return TIPO_COLOR["dnd"]
    if "magic"     in n:                                  return TIPO_COLOR["magic"]
    if "tcg"       in n or "carta"  in n:                 return TIPO_COLOR["tcg"]
    if "bingo"     in n:                                  return TIPO_COLOR["bingo"]
    if "pintura"   in n:                                  return TIPO_COLOR["pintura"]
    if "virus"     in n:                                  return TIPO_COLOR["virus"]
    if "mesa"      in n or "juego"  in n:                 return TIPO_COLOR["mesa"]
    return TIPO_COLOR["default"]


def _remove_black_bg(logo_path, tolerance=40):
    """
    Elimina el fondo usando scipy.ndimage (vectorizado, sin bucle Python).
    - Si el PNG ya tiene canal alpha real → lo usa directamente (más rápido)
    - Si no → detecta el color de fondo desde las esquinas y aplica flood-fill
      vectorizado con ndimage.label (4x más rápido que deque píxel a píxel)
    - Cache por ruta: cada archivo se procesa una sola vez aunque se use N veces
    """
    key = str(logo_path)
    if key in _IMG_CACHE:
        return _IMG_CACHE[key].copy()

    img = Image.open(logo_path)

    # Atajo: PNG con transparencia real ya lista
    if img.mode == "RGBA":
        arr = np.array(img)
        if arr[:,:,3].min() == 0:
            _IMG_CACHE[key] = img
            return img.copy()

    img = img.convert("RGBA")
    arr = np.array(img, dtype=np.int16)
    h, w = arr.shape[:2]

    # Color de fondo = color más frecuente en los 4 bordes (robusto ante variaciones)
    border_pixels = np.concatenate([
        arr[0,:,:3], arr[-1,:,:3], arr[:,0,:3], arr[:,-1,:3]
    ])
    quantized = (border_pixels // 10) * 10
    unique, counts = np.unique(quantized.reshape(-1,3), axis=0, return_counts=True)
    bg_color = unique[counts.argmax()].astype(float)

    # Máscara binaria de píxeles similares al fondo
    bg_mask = (np.abs(arr[:,:,:3] - bg_color).max(axis=2) < tolerance).astype(np.uint8)

    # Seed = píxeles de borde que pertenecen al fondo
    seed = np.zeros_like(bg_mask)
    seed[0,:]  = bg_mask[0,:]
    seed[-1,:] = bg_mask[-1,:]
    seed[:,0]  = bg_mask[:,0]
    seed[:,-1] = bg_mask[:,-1]

    # ndimage.label agrupa regiones conectadas vectorialmente
    labeled, _ = ndimage.label(bg_mask)
    border_labels = set(labeled[seed.astype(bool)]) - {0}
    bg_region = np.isin(labeled, list(border_labels))

    alpha = np.where(bg_region, 0, 255).astype(np.uint8)
    result = Image.fromarray(arr.astype(np.uint8))
    result.putalpha(Image.fromarray(alpha))

    _IMG_CACHE[key] = result
    return result.copy()


def _compose_on_bg(icon_rgba, bg_color):
    """Compone un icono RGBA sobre un color sólido — resultado siempre RGB sin alpha."""
    bg = Image.new("RGBA", icon_rgba.size, (*bg_color, 255))
    return Image.alpha_composite(bg, icon_rgba).convert("RGB")


def _load_icon(path, size, bg_color=None):
    """Carga, quita fondo, recorta márgenes y escala un icono. Listo para pegar."""
    img = _remove_black_bg(path)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    img.thumbnail((size, size), Image.LANCZOS)
    if bg_color:
        img = _compose_on_bg(img, bg_color)
    return img


def _paste_logo(canvas, path, cx, cy, size):
    """Pega logo centrado en (cx,cy) con composición segura cross-platform."""
    try:
        logo = _load_icon(path, size, bg_color=C["bg"])
        canvas.paste(logo, (cx - logo.width//2, cy - logo.height//2))
    except Exception as e:
        print(f"  [warn] logo: {e}")


def _gradient_bg(canvas):
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        t = y/H
        arr[y] = [int(10+14*t), int(10+8*t), int(16+22*t)]
    canvas.paste(Image.fromarray(arr,"RGB"), (0,0))


def _noise(canvas, s=5):
    arr = np.array(canvas).astype(np.int16)
    arr = np.clip(arr+np.random.randint(-s,s,arr.shape,dtype=np.int16),0,255)
    return Image.fromarray(arr.astype(np.uint8))


def _tcx(draw, text, font, y, color, x0=0, x1=W):
    bb = draw.textbbox((0,0), text, font=font)
    draw.text(((x0+x1-bb[2]+bb[0])//2, y), text, font=font, fill=color)


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur+" "+w).strip()
        if draw.textbbox((0,0),test,font=font)[2] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines


def _find_key(semana, dia_base):
    if dia_base in semana: return dia_base
    for k in semana:
        if k.upper().startswith(dia_base): return k
    return dia_base


def _altura_tarjeta(eventos, col_w):
    """Calcula altura exacta usando wrap real según el ancho de columna."""
    TW = col_w - 28
    if not eventos:
        return HCARD + PAD_TOP + 44 + 14

    _f_ev   = fnt("bold",  36)
    _f_desc = fnt("serif", 24)

    def _wrap_h(text, font, lh):
        img_tmp  = Image.new("RGB", (10, 10))
        draw_tmp = ImageDraw.Draw(img_tmp)
        words, lines, cur = text.split(), [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if draw_tmp.textbbox((0,0), test, font=font)[2] <= TW:
                cur = test
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        return max(1, len(lines)) * lh

    total = HCARD + PAD_TOP
    for i, ev in enumerate(eventos):
        if i > 0: total += SEP_H
        total += ICON_SZ + 6
        total += LH_HORA + 3
        total += _wrap_h(ev.get("nombre","x"), _f_ev, LH_EVM) + 4
        desc = ev.get("descripcion","")
        if desc:
            total += _wrap_h(desc, _f_desc, LH_DESC) + 6
    return total + 16


# ── FUNCIÓN PRINCIPAL ─────────────────────────────────────────────────────────

def generar_agenda(
    semana:       dict,
    logos:        list = None,
    output:       str  = "agenda_semanal.png",
    titulo:       str  = "AGENDA SEMANAL",
    semana_label: str  = "",
    week_start:   str  = "",
    direccion:    str  = "Av. 12E # 2-100 Quinta Oriental",
    subtitulo:    str  = "tienda de juegos · rol · coleccionables",
):
    logos = logos or []
    global H

    day_numbers = {}
    DIAS_BASE = ["LUNES","MARTES","MIÉRCOLES","JUEVES","VIERNES","SÁBADO","DOMINGO"]
    if week_start:
        try:
            lunes = date.fromisoformat(week_start)
            for i, d in enumerate(DIAS_BASE):
                day_numbers[d] = (lunes + timedelta(days=i)).day
        except Exception as e:
            print(f"  [warn] {e}")

    # Calcular H exacto
    COL_W_tmp  = (W - 2*GPAD - CGAP) // 2
    _col_izq_h = sum(_altura_tarjeta(semana.get(_find_key(semana,d),[]), COL_W_tmp)
                     for d in ["LUNES","MARTES","MIÉRCOLES","JUEVES"]) + RGAP*3
    _col_der_h = sum(_altura_tarjeta(semana.get(_find_key(semana,d),[]), COL_W_tmp)
                     for d in ["VIERNES","SÁBADO","DOMINGO"]) + RGAP*2
    _HEADER_H  = 360
    _GRID_TOP  = _HEADER_H + 8 + 22
    H = _GRID_TOP + max(_col_izq_h, _col_der_h) + 20 + 160
    print(f"  Canvas calculado: {W}×{H}px")

    canvas = Image.new("RGB", (W, H), C["bg"])
    _gradient_bg(canvas)
    draw = ImageDraw.Draw(canvas)

    for i in range(-H, W+H, 150):
        draw.line([(i,0),(i+H,H)], fill=(255,255,255,3), width=1)

    # ── HEADER ────────────────────────────────────────────────────────────────
    HEADER_H = 360

    for i in range(7):
        draw.rectangle([0, i, W, i+1], fill=(*C["accent"], max(80, 255-i*34)))

    for idx, path in enumerate(logos[:3]):
        cx = [140, W//2, W-140][idx]
        cy = [114, 106, 114][idx]
        sz = [118, 140, 118][idx]
        _paste_logo(canvas, path, cx, cy, sz)

    _tcx(draw, titulo, fnt("bold_i", 96), 188, C["text_hi"])

    if semana_label:
        _tcx(draw, semana_label.upper(), fnt("bold", 40), 296, C["accent"])

    DIV_Y = HEADER_H + 8
    PAD   = 55
    draw.rectangle([PAD, DIV_Y, W//2-30, DIV_Y+3], fill=C["accent"])
    draw.rectangle([W//2+30, DIV_Y, W-PAD, DIV_Y+3], fill=C["accent"])
    draw.polygon([(W//2,DIV_Y-10),(W//2+12,DIV_Y+2),
                  (W//2,DIV_Y+12),(W//2-12,DIV_Y+2)], fill=C["accent"])

    # ── GRID 2 COLUMNAS ───────────────────────────────────────────────────────
    GRID_TOP = DIV_Y + 22
    COL_W    = (W - 2*GPAD - CGAP) // 2

    COL_IZQ = ["LUNES","MARTES","MIÉRCOLES","JUEVES"]
    COL_DER = ["VIERNES","SÁBADO","DOMINGO"]

    F_DNAME  = fnt("bold_i", 30)
    F_HORA   = fnt("regular", 26)
    F_EV1    = fnt("bold",    40)
    F_EVM    = fnt("bold",    36)
    F_DESC   = fnt("serif",   24)
    F_EMPTY  = fnt("serif",   26)

    def dibujar_columna(dias_col, col_x):
        ty = GRID_TOP
        for dia_base in dias_col:
            dia_key = _find_key(semana, dia_base)
            eventos = semana.get(dia_key, [])
            card_h  = _altura_tarjeta(eventos, COL_W)

            x0, y0 = col_x, ty
            x1, y1 = col_x + COL_W, ty + card_h
            TW      = COL_W - 2*14
            BOTTOM  = y1 - 10

            draw.rounded_rectangle([x0,y0,x1,y1], radius=14,
                                    fill=C["card"], outline=C["border"], width=1)
            draw.rounded_rectangle([x0,y0,x1,y0+HCARD], radius=14, fill=C["accent"])
            draw.rectangle([x0, y0+HCARD-14, x1, y0+HCARD], fill=C["accent"])

            num       = day_numbers.get(dia_base, "")
            label_dia = f"{dia_base[:9]}  {num}" if num else dia_base[:9]
            _tcx(draw, label_dia, F_DNAME, y0+16, C["white"], x0, x1)

            def put(text, font, color, lh, cur_ty):
                for line in _wrap(draw, text, font, TW):
                    if cur_ty + lh > BOTTOM: return None
                    draw.text((x0+14, cur_ty), line, font=font, fill=color)
                    cur_ty += lh
                return cur_ty

            ey = y0 + HCARD + PAD_TOP

            if not eventos:
                draw.text((x0+14, ey+10), "Sin eventos.",
                          font=F_EMPTY, fill=C["text_lo"])
            else:
                f_nombre  = F_EV1 if len(eventos)==1 else F_EVM
                lh_nombre = LH_EV1 if len(eventos)==1 else LH_EVM

                for i, ev in enumerate(eventos):
                    if ey + ICON_SZ + LH_HORA > BOTTOM: break

                    nombre   = ev.get("nombre","")
                    hora     = ev.get("hora","")
                    desc     = ev.get("descripcion","")
                    img_path = ev.get("imagen","")

                    if i > 0:
                        draw.rectangle([x0+14, ey, x1-14, ey+1], fill=C["border"])
                        ey += SEP_H

                    if img_path and Path(img_path).exists():
                        try:
                            icon = _load_icon(img_path, ICON_SZ, bg_color=C["card"])
                            # Alineado a la izquierda, centrado verticalmente en el bloque ICON_SZ
                            icon_x = x0 + 14
                            icon_y = ey + (ICON_SZ - icon.height) // 2
                            canvas.paste(icon, (icon_x, icon_y))
                        except Exception: pass
                    ey += ICON_SZ + 6

                    if ey + LH_HORA > BOTTOM: break
                    draw.text((x0+14, ey), hora, font=F_HORA, fill=C["text_mid"])
                    ey += LH_HORA + 3

                    res = put(nombre, f_nombre, C["text_hi"], lh_nombre, ey)
                    if res is None: break
                    ey = res + 4

                    if desc:
                        res = put(desc, F_DESC, C["text_mid"], LH_DESC, ey)
                        if res: ey = res + 6

            ty += card_h + RGAP

    dibujar_columna(COL_IZQ, GPAD)
    dibujar_columna(COL_DER, GPAD + COL_W + CGAP)

    # ── FOOTER ────────────────────────────────────────────────────────────────
    col_izq_h = sum(_altura_tarjeta(semana.get(_find_key(semana,d),[]), COL_W)
                   for d in COL_IZQ) + RGAP*3
    col_der_h = sum(_altura_tarjeta(semana.get(_find_key(semana,d),[]), COL_W)
                   for d in COL_DER) + RGAP*2
    FY = GRID_TOP + max(col_izq_h, col_der_h) + 20

    draw.rectangle([0, FY, W, H], fill=C["footer_bg"])
    draw.rectangle([0, FY, W, FY+4], fill=C["accent"])

    f_addr = fnt("bold",    30)
    f_sub  = fnt("regular", 24)

    addr_bb = draw.textbbox((0,0), direccion, font=f_addr)
    addr_w  = addr_bb[2] - addr_bb[0]
    addr_x  = (W - addr_w - 20) // 2
    addr_y  = FY + 24

    draw.ellipse([addr_x, addr_y+7, addr_x+16, addr_y+23], fill=C["accent"])
    draw.text((addr_x+22, addr_y), direccion, font=f_addr, fill=C["white"])

    if subtitulo:
        _tcx(draw, subtitulo, f_sub, addr_y+50, C["text_mid"])

    for i in range(6):
        draw.rectangle([0,H-6+i,W,H-5+i], fill=(*C["accent"], max(60,255-i*44)))

    canvas = _noise(canvas)
    canvas.save(output, "PNG")
    print(f"✅  {output}  ({W}×{H}px)")
    return output


# ── DATOS ─────────────────────────────────────────────────────────────────────

SEMANA = {
    "LUNES 23": [
        {"nombre": "Altered TCG",
         "hora": "3:00 – 6:00 PM", "descripcion": "Partidas abiertas",
         "imagen": "altered.png"},
        {"nombre": "Warhammer 40K",
         "hora": "3:00 – 6:00 PM", "descripcion": "Batallas y pintura de minis",
         "imagen": "40k.png"},
        {"nombre": "Día del Virus",
         "hora": "Todo el día",
         "descripcion": "Juegos de mesa + nuevo juego en tienda",
         "imagen": "virus.png"},
    ],
    "MARTES": [
        {"nombre": "Calabozos y Dragones",
         "hora": "3:00 – 6:00 PM", "descripcion": "Campaña Oneshot semanal abierta",
         "imagen": "DnD.png"},
    ],
    "MIÉRCOLES": [
        {"nombre": "Pokémon TCG",
         "hora": "3:00 – 6:00 PM", "descripcion": "Torneos y casual",
         "imagen": "Playpkmn.png"},
        {"nombre": "D&D",
         "hora": "3:00 – 6:00 PM", "descripcion": "Mesa abierta",
         "imagen": "DnD.png"},
    ],
    "JUEVES": [],
    "VIERNES": [
        {"nombre": "Bingo",
         "hora": "6:00 – 9:00 PM", "descripcion": "Premios y diversión",
         "imagen": "Cueva.png"},
        {"nombre": "Juegos de Mesa",
         "hora": "3:00 – 9:00 PM", "descripcion": "Gran variedad de títulos",
         "imagen": "Cueva.png"},
    ],
    "SÁBADO": [
        {"nombre": "Magic: The Gathering",
         "hora": "3:00 – 6:00 PM", "descripcion": "Commander Party",
         "imagen": "MTG.png"},
        {"nombre": "TCGs Abierto",
         "hora": "3:00 – 6:00 PM", "descripcion": "Altered, Lorcana y más",
         "imagen": "Nishi.png"},
        {"nombre": "Calabozos y Dragones",
         "hora": "3:00 – 6:00 PM", "descripcion": "Mesa de campaña Tomb of Horrors",
         "imagen": "DnD.png"},
    ],
    "DOMINGO": [
        {"nombre": "Yu-Gi-Oh!",
         "hora": "2:45 – 6:00 PM", "descripcion": "Torneo Avanzado",
         "imagen": "OTS.png"},
        {"nombre": "Día de Pintura",
         "hora": "3:00 – 6:00 PM", "descripcion": "Miniaturas Warhammer",
         "imagen": "Cueva.png"},
    ],
}

if __name__ == "__main__":
    generar_agenda(
        semana=SEMANA,
        logos=["Nishi.png", "Cueva.png", "Victory.png"],
        output="agenda_semanal.png",
        titulo="AGENDA SEMANAL",
        semana_label="Mar. 23 – 29, 2026",
        week_start="2026-03-23",
        direccion="Av. 12E # 2-100 Quinta Oriental",
        subtitulo="Cueva del Búho · Victory Road · Nishi",
    )
