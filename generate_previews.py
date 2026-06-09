#!/usr/bin/env python3
"""
Generador y sincronizador de catálogos — En Un Clic
====================================================

Genera TODAS las imágenes del catálogo componiendo las fotos de producto desde
la biblioteca local (product-images/{categoria}/{slug}.{ext}). Sin precios en
las imágenes: solo nombre + descripción.

WORKFLOW:
  1. Editá los datos en COMBOS o PRODUCTOS_INDIVIDUALES abajo
  2. (Opcional) actualizá fotos en product-images/{categoria}/{slug}.{ext}
  3. Corré: python3 generate_previews.py
  4. Hacé push al repo

Comandos:
  python3 generate_previews.py              # imágenes + sync DB (todo)
  python3 generate_previews.py images       # solo regenera TODAS las imágenes
  python3 generate_previews.py sync-db      # solo sincroniza la DB

Requiere:
  pip install Pillow
  Variables de entorno (solo para sync-db):
    SUPABASE_URL, SUPABASE_KEY (service_role), TENANT_ID
"""

import os, sys, json, math, glob, urllib.request
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageChops

# ── Config DB — solo desde variables de entorno, nunca hardcodeado ────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
TENANT_ID    = os.getenv("TENANT_ID",    "")
BASE_IMG_URL = "https://raw.githubusercontent.com/marcoslozina/en-un-clic-catalogs/main"

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_DIR   = os.path.dirname(os.path.abspath(__file__))
IMG_LIB    = os.path.join(REPO_DIR, "product-images")   # biblioteca local por categoría

# ── Fonts (con fallback robusto) ──────────────────────────────────────────────
def _font_path(*candidates):
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

FONT_BOLD  = _font_path("/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf")
FONT_REG   = _font_path("/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf")
FONT_BLACK = _font_path("/usr/share/fonts/truetype/msttcorefonts/Arial_Black.ttf",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                        FONT_BOLD)

# ── Brand / paleta ────────────────────────────────────────────────────────────
GOLD       = (198, 158, 47)
WHITE      = (255, 255, 255)
DARK_TEXT  = (40, 40, 40)
DESC_TEXT  = (120, 100, 70)     # subtítulo de descripción (bronce apagado, alto contraste sobre blanco)
SEPARATOR  = (224, 214, 188)
DESC_BG    = (255, 250, 230)    # banda de descripción de combos (champagne)
WM_COLOR   = (198, 158, 47)     # watermark dorado (visible sobre fondo blanco)
WM_MAX_A   = 60                 # opacidad máxima del watermark (en la base)
W, H       = 1080, 1350
WHATSAPP   = "+54 376 541-3840"
FOOTER_TXT = "Entrega en el dia en Posadas • Todo el pais"
HEADER_H   = 210
FOOTER_H   = 92

CAT_TITLES = {
    "cara":    "Skincare Facial",
    "cuerpo":  "Cuidado Corporal",
    "manos":   "Manos",
    "capilar": "Cabello",
}

# ═════════════════════════════════════════════════════════════════════════════
#  FUENTE DE VERDAD — editá estos datos para actualizar precios / productos
#  (Los precios se usan SOLO para la DB; NO se dibujan en las imágenes.)
# ═════════════════════════════════════════════════════════════════════════════

# COMBOS — 'items' lista los slugs de productos que se componen en la imagen
COMBOS = [
    {
        "name": "Experiencia Spa Total", "slug": "experiencia-spa-total",
        "description": "Incluye 8 productos: Mousse Limpiadora · Sérum Vit C · Protector Solar · Gel Ducha · Exfoliante · Loción Corporal · Champú · Aceite Capilar",
        "price": 72000, "productos": 8, "stock": 30,
        "items": ["cara-mousse-limpiadora", "cara-serum-vit-c", "cara-protector-solar",
                  "cuerpo-gel-ducha", "cuerpo-exfoliante", "cuerpo-locion",
                  "capilar-champu", "capilar-aceite"],
    },
    {
        "name": "Piel de Seda Corporal", "slug": "piel-seda-corporal",
        "description": "Incluye: Gel de Ducha Rose 500ml · Exfoliante Melocotón 250g · Loción Niacinamida 250ml",
        "price": 33000, "productos": 3, "stock": 50,
        "items": ["cuerpo-gel-ducha", "cuerpo-exfoliante", "cuerpo-locion"],
    },
    {
        "name": "Melena de Ensueño", "slug": "melena-sueno",
        "description": "Incluye: Champú Anticaspa Romero 500ml · Mascarilla Queratina 500ml · Aceite Reparador Puré de Arroz",
        "price": 30500, "productos": 3, "stock": 50,
        "items": ["capilar-champu", "capilar-mascarilla", "capilar-aceite"],
    },
    {
        "name": "Reparación Nocturna", "slug": "reparacion-nocturna",
        "description": "Incluye: Limpiador Retinol · Sérum Retinol+Cafeína · Crema de Ojos · Crema Colágeno Perla",
        "price": 24500, "productos": 4, "stock": 50,
        "items": ["cara-limpiador-retinol", "cara-serum-retinol", "cara-crema-ojos", "cara-crema-perla"],
    },
    {
        "name": "Mañana Radiante", "slug": "manana-radiante",
        "description": "Incluye: Limpiador Vitamina C · Sérum Vitamina C 100ml · Protector Solar SPF50+",
        "price": 14500, "productos": 3, "stock": 50,
        "items": ["cara-limpiador-vitc", "cara-serum-vit-c", "cara-protector-solar"],
    },
    {
        "name": "Manos de Terciopelo", "slug": "manos-terciopelo",
        "description": "Incluye: Crema Manos Naranja 150g · Crema Niacinamida 30g · Crema Anti-grietas 60g",
        "price": 9400, "productos": 3, "stock": 50,
        "items": ["manos-crema-naranja", "manos-crema-niaci", "manos-anti-agrietadas"],
    },
]

# PRODUCTOS INDIVIDUALES por categoría — precio DESC dentro de cada una
PRODUCTOS_INDIVIDUALES = {
    "cara": [
        {"name": "Crema Reparadora Perla",      "sku": "cara-crema-perla",       "price": 11000, "description": "Colágeno SADOER 70g",             "stock": 30},
        {"name": "Mousse Limpiadora Puré",       "sku": "cara-mousse-limpiadora", "price":  7700, "description": "de Arroz BIOAQUA 120ml",           "stock": 40},
        {"name": "Sérum Vitamina C 100ml",       "sku": "cara-serum-vit-c",       "price":  7300, "description": "SADOER",                           "stock": 40},
        {"name": "Limpiador Reafirmante",        "sku": "cara-limpiador-retinol", "price":  6300, "description": "Retinol BIOAQUA 100g",             "stock": 40},
        {"name": "Crema de Ojos Cafeína",        "sku": "cara-crema-ojos",        "price":  4300, "description": "Antiarrugas SADOER 20g",           "stock": 40},
        {"name": "Limpiador Iluminador C",       "sku": "cara-limpiador-vitc",    "price":  3800, "description": "Vitamina SADOER",                  "stock": 40},
        {"name": "Protector Solar Puré",         "sku": "cara-protector-solar",   "price":  3500, "description": "de Arroz BIOAQUA SPF50+",          "stock": 40},
        {"name": "Sérum Antiarrugas + Cafeína",  "sku": "cara-serum-retinol",     "price":  2900, "description": "Retinol Cafeína SADOER 30ml",      "stock": 40},
    ],
    "cuerpo": [
        {"name": "Gel de Ducha Rose",            "sku": "cuerpo-gel-ducha",       "price": 15000, "description": "BIOAQUA 500ml",                    "stock": 40},
        {"name": "Loción Corporal Niacinamida",  "sku": "cuerpo-locion",          "price": 10500, "description": "Blanqueadora SADOER 250ml",        "stock": 40},
        {"name": "Exfoliante Rejuvenecedor",     "sku": "cuerpo-exfoliante",      "price":  7800, "description": "Melocotón BIOAQUA 250g",           "stock": 40},
    ],
    "manos": [
        {"name": "Crema de Manos Naranja",       "sku": "manos-crema-naranja",    "price":  6300, "description": "VC Vaselina SADOER 150g",          "stock": 40},
        {"name": "Crema Anti-Agrietadas",        "sku": "manos-anti-agrietadas",  "price":  2100, "description": "Manos y Pies SADOER 60g",          "stock": 40},
        {"name": "Crema Manos Niacinamida",      "sku": "manos-crema-niaci",      "price":  1100, "description": "Radiante SADOER 30g",              "stock": 40},
    ],
    "capilar": [
        {"name": "Champú Anticaspa Romero",      "sku": "capilar-champu",         "price": 13500, "description": "SADOER 500ml",                     "stock": 40},
        {"name": "Mascarilla Reparadora",        "sku": "capilar-mascarilla",     "price": 11500, "description": "Queratina SADOER 500ml",           "stock": 40},
        {"name": "Aceite Reparador Cabello",     "sku": "capilar-aceite",         "price":  6100, "description": "Puré de Arroz BIOAQUA 70ml",       "stock": 40},
    ],
}

# Índice slug → producto (para resolver miembros de combos)
PROD_BY_SLUG = {p["sku"]: p for prods in PRODUCTOS_INDIVIDUALES.values() for p in prods}

# ═════════════════════════════════════════════════════════════════════════════
#  Helpers de imagen
# ═════════════════════════════════════════════════════════════════════════════

def fnt(path, size):
    return ImageFont.truetype(path, size)

def _tw(draw, text, font):
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0]

def centered(draw, text, y, font, color, x=0, width=W):
    """Centra el texto horizontalmente dentro de [x, x+width]."""
    tw = _tw(draw, text, font)
    draw.text((x + (width - tw) // 2, y), text, font=font, fill=color)

def pixel_wrap(text, draw, font, max_px):
    """Wrap por ancho real en píxeles — evita cortes con cualquier fuente/tamaño."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = cur + (" " if cur else "") + w
        if _tw(draw, test, font) > max_px and cur:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def _lib_photo(slug):
    """Ruta de la foto del producto en la biblioteca local (cualquier extensión)."""
    folder = slug.split("-", 1)[0]   # cara-serum-vit-c → cara
    matches = sorted(glob.glob(os.path.join(IMG_LIB, folder, f"{slug}.*")))
    return matches[0] if matches else None


def autotrim(img):
    """Recorta el margen de fondo uniforme (blanco/transparente) que rodea al producto,
    para que todos llenen su celda parejo (soluciona el 'producto mucho más chico')."""
    rgba = img.convert("RGBA")
    w, h = rgba.size
    corners = [rgba.getpixel((0, 0)), rgba.getpixel((w - 1, 0)),
               rgba.getpixel((0, h - 1)), rgba.getpixel((w - 1, h - 1))]
    if max(c[3] for c in corners) < 10:
        bbox = rgba.getchannel("A").getbbox()
    else:
        bg = corners[0][:3]
        diff = ImageChops.difference(rgba.convert("RGB"), Image.new("RGB", rgba.size, bg)).convert("L")
        bbox = diff.point(lambda p: 255 if p > 18 else 0).getbbox()
    if not bbox:
        return rgba
    x0, y0, x1, y1 = bbox
    if (x1 - x0) > w * 0.97 and (y1 - y0) > h * 0.97:
        return rgba
    pad = 6
    return rgba.crop((max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)))


def fit_contain(img, box_w, box_h):
    """Escala (en ambos sentidos) preservando aspect ratio para llenar la celda."""
    scale = min(box_w / img.width, box_h / img.height)
    nw, nh = max(1, round(img.width * scale)), max(1, round(img.height * scale))
    return img.resize((nw, nh), Image.LANCZOS)


def draw_product_cell(canvas, draw, box, prod):
    """Dibuja una celda de producto: foto (auto-trim + contain), nombre (bold) y
    descripción (subtítulo) — TODO centrado, sin precios. El texto se ubica debajo
    de la foto con espacio reservado para no chocar con las líneas separadoras."""
    x, y, w, h = box
    pad     = 20
    TEXT_H  = 132                      # bloque reservado para nombre + descripción
    photo_h = h - TEXT_H

    path = _lib_photo(prod["sku"])
    if path:
        try:
            photo  = autotrim(Image.open(path))
            fitted = fit_contain(photo, int(w * 0.72), int(photo_h * 0.84))
            px = x + (w - fitted.width) // 2
            py = y + (photo_h - fitted.height) // 2 + 6
            canvas.paste(fitted, (px, py), fitted)
        except Exception as exc:
            print(f"    ⚠ {prod['sku']}: no se pudo componer ({exc})")

    f_name = fnt(FONT_BOLD, 30)
    f_desc = fnt(FONT_REG, 24)
    ty = y + photo_h + 2
    for ln in pixel_wrap(prod["name"], draw, f_name, w - 2 * pad)[:2]:
        centered(draw, ln, ty, f_name, DARK_TEXT, x, w)
        ty += 34
    for ln in pixel_wrap(prod["description"], draw, f_desc, w - 2 * pad)[:2]:
        centered(draw, ln, ty, f_desc, DESC_TEXT, x, w)
        ty += 28


def draw_header(draw, title, subtitle):
    draw.rectangle([0, 0, W, HEADER_H], fill=GOLD)
    centered(draw, "En Un Clic", 34, fnt(FONT_BOLD, 46), WHITE)
    f_sub = fnt(FONT_BLACK, 58)
    while _tw(draw, title, f_sub) > W - 80 and f_sub.size > 30:
        f_sub = fnt(FONT_BLACK, f_sub.size - 2)
    centered(draw, title, 92, f_sub, WHITE)
    if subtitle:
        centered(draw, subtitle, 170, fnt(FONT_BOLD, 28), WHITE)


def draw_footer(draw):
    y0 = H - FOOTER_H
    draw.rectangle([0, y0, W, H], fill=GOLD)
    centered(draw, f"WhatsApp: {WHATSAPP}", y0 + 16, fnt(FONT_BOLD, 34), WHITE)
    centered(draw, FOOTER_TXT,              y0 + 56, fnt(FONT_REG,  26), WHITE)


def add_bottom_watermark(img, text="EN UN CLIC"):
    """Marca de agua GRANDE 'EN UN CLIC' en la franja inferior, con gradiente de
    opacidad de abajo (más fuerte) hacia arriba (se desvanece). Color dorado para
    ser visible sobre el fondo blanco sin tapar los productos."""
    img = img.convert("RGBA")
    w, h = img.size
    size = 132
    font = fnt(FONT_BLACK, size)
    d0 = ImageDraw.Draw(img)
    while _tw(d0, text, font) > w - 70 and size > 40:
        size -= 4
        font = fnt(FONT_BLACK, size)
    tw = _tw(d0, text, font)
    th = d0.textbbox((0, 0), text, font=font)[3]
    tx = (w - tw) // 2
    base_y = h - FOOTER_H - 20          # base del texto, justo arriba del footer
    ty = base_y - th

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((tx, ty), text, font=font, fill=(*WM_COLOR, 255))

    grad = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(grad)
    span = max(1, base_y - ty)
    for yy in range(h):
        a = 0 if yy < ty else (WM_MAX_A if yy > base_y else int(WM_MAX_A * (yy - ty) / span))
        gd.line([(0, yy), (w, yy)], fill=a)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), grad))
    return Image.alpha_composite(img, layer).convert("RGB")


# ═════════════════════════════════════════════════════════════════════════════
#  Generadores de imágenes
# ═════════════════════════════════════════════════════════════════════════════

def _grid(canvas, draw, products, top, bottom):
    """Dibuja una grilla de 2 columnas de productos entre top y bottom."""
    n     = len(products)
    rows  = math.ceil(n / 2)
    col_w = W // 2
    row_h = (bottom - top) // rows
    for i, prod in enumerate(products):
        r, c = divmod(i, 2)
        x = c * col_w
        y = top + r * row_h
        draw_product_cell(canvas, draw, (x, y, col_w, row_h), prod)
        # separador horizontal al fondo de la fila (no en la última fila)
        if r < rows - 1:
            ly = top + (r + 1) * row_h - 4
            draw.line([(40, ly), (W - 40, ly)], fill=SEPARATOR, width=2)


def generate_category(cat, products):
    out = os.path.join(REPO_DIR, f"preview_{cat}.jpg")
    canvas = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, CAT_TITLES.get(cat, cat.title()), None)
    _grid(canvas, draw, products, HEADER_H + 6, H - FOOTER_H)
    draw_footer(draw)
    canvas = add_bottom_watermark(canvas)
    canvas.save(out, "JPEG", quality=92)
    print(f"  ✓ {os.path.basename(out)}")


def generate_combo(combo):
    out = os.path.join(REPO_DIR, f"preview_combo-{combo['slug']}.jpg")
    canvas = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(canvas)

    # Header (sin precio)
    draw_header(draw, combo["name"], f"* {combo['productos']} productos incluidos")

    # Banda de descripción
    DESC_BAND_H = 78
    draw.rectangle([0, HEADER_H, W, HEADER_H + DESC_BAND_H], fill=DESC_BG)
    f_band = fnt(FONT_REG, 24)
    lines = pixel_wrap(combo["description"], draw, f_band, W - 80)[:2]
    if len(lines) == 1:
        centered(draw, lines[0], HEADER_H + 26, f_band, DARK_TEXT)
    else:
        centered(draw, lines[0], HEADER_H + 12, f_band, DARK_TEXT)
        centered(draw, lines[1], HEADER_H + 44, f_band, DARK_TEXT)

    # Grilla de productos miembro
    members = [PROD_BY_SLUG[s] for s in combo.get("items", []) if s in PROD_BY_SLUG]
    _grid(canvas, draw, members, HEADER_H + DESC_BAND_H + 6, H - FOOTER_H)

    draw_footer(draw)
    canvas = add_bottom_watermark(canvas)
    canvas.save(out, "JPEG", quality=92)
    print(f"  ✓ {os.path.basename(out)}")


def generate_combos_list():
    """preview_combos.jpg — lista de combos (nombre + descripción, SIN precios)."""
    out = os.path.join(REPO_DIR, "preview_combos.jpg")
    canvas = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, "Combos Skincare", None)

    top, bottom = HEADER_H + 20, H - FOOTER_H
    row_h = (bottom - top) // len(COMBOS)
    f_name = fnt(FONT_BOLD, 38)
    f_desc = fnt(FONT_REG, 25)
    ml = 60
    for i, combo in enumerate(COMBOS):
        y = top + i * row_h
        draw.text((ml, y + 12), combo["name"], font=f_name, fill=DARK_TEXT)
        for li, dl in enumerate(pixel_wrap(combo["description"], draw, f_desc, W - 2 * ml)[:3]):
            draw.text((ml, y + 60 + li * 30), dl, font=f_desc, fill=DESC_TEXT)
        if i < len(COMBOS) - 1:
            draw.line([(ml, y + row_h - 10), (W - ml, y + row_h - 10)], fill=SEPARATOR, width=2)

    draw_footer(draw)
    canvas = add_bottom_watermark(canvas)
    canvas.save(out, "JPEG", quality=92)
    print(f"  ✓ {os.path.basename(out)}")


def generate_all_images():
    print("▸ Grillas de categoría...")
    for cat, products in PRODUCTOS_INDIVIDUALES.items():
        generate_category(cat, products)
    print("▸ Combos...")
    for combo in COMBOS:
        generate_combo(combo)
    print("▸ Lista de combos...")
    generate_combos_list()

    # Validación: todas las imágenes deben medir W×H
    print(f"▸ Validando tamaño uniforme ({W}×{H})...")
    bad = []
    for f in sorted(glob.glob(os.path.join(REPO_DIR, "preview_*.jpg"))):
        with Image.open(f) as im:
            if im.size != (W, H):
                bad.append((os.path.basename(f), im.size))
    if bad:
        for name, size in bad:
            print(f"  ✗ {name}: {size}", file=sys.stderr)
        sys.exit(1)
    print(f"  ✓ Todas las imágenes miden {W}×{H}")


# ═════════════════════════════════════════════════════════════════════════════
#  Sync DB  (los precios SÍ van a la DB — el bot los necesita para vender)
# ═════════════════════════════════════════════════════════════════════════════

def _supabase_req(method, path, body=None, extra_headers=None):
    headers = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "resolution=merge-duplicates,return=representation",
    }
    if extra_headers:
        headers.update(extra_headers)
    data = json.dumps(body).encode() if body is not None else None
    req  = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}", data=data,
                                   headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else []


def sync_db():
    """Upsert products a la DB usando SKU como clave única."""
    missing = [v for v in ("SUPABASE_URL", "SUPABASE_KEY", "TENANT_ID") if not os.getenv(v)]
    if missing:
        print(f"  ✗ Faltan variables de entorno: {', '.join(missing)}")
        for v in missing:
            print(f"      export {v}=...")
        sys.exit(1)

    rows = []
    for c in COMBOS:
        rows.append({
            "tenant_id": TENANT_ID, "sku": f"combo-{c['slug']}", "name": c["name"],
            "description": c["description"], "category": "combos", "price": c["price"],
            "currency": "ARS", "stock": c["stock"], "stock_min": 3, "active": True,
            "metadata": {"image_url": f"{BASE_IMG_URL}/preview_combo-{c['slug']}.jpg",
                         "n_products": c["productos"]},
        })
    for cat, products in PRODUCTOS_INDIVIDUALES.items():
        for p in products:
            rows.append({
                "tenant_id": TENANT_ID, "sku": p["sku"], "name": p["name"],
                "description": p["description"], "category": cat, "price": p["price"],
                "currency": "ARS", "stock": p["stock"], "stock_min": 5, "active": True,
                "metadata": {},
            })

    incoming_by_key = {(r["category"], r["name"]): r["sku"] for r in rows}
    existing = _supabase_req("GET", f"products?tenant_id=eq.{TENANT_ID}&select=id,sku,name,category")
    stale_ids = [p["id"] for p in existing
                 if (p["category"], p["name"]) in incoming_by_key
                 and p["sku"] != incoming_by_key[(p["category"], p["name"])]]
    if stale_ids:
        _supabase_req("DELETE", f"products?id=in.({','.join(stale_ids)})&tenant_id=eq.{TENANT_ID}")
        print(f"  ⚠ {len(stale_ids)} producto(s) obsoleto(s) eliminados (SKU cambió)")

    result = _supabase_req("POST", "products?on_conflict=tenant_id,sku", rows)
    print(f"  ✓ {len(result)} productos upserted en DB")

    tenants = _supabase_req("GET", f"tenants?id=eq.{TENANT_ID}&select=retail_config")
    if tenants:
        rc = tenants[0].get("retail_config") or {}
        rc["catalog_base_url"] = BASE_IMG_URL
        _supabase_req("PATCH", f"tenants?id=eq.{TENANT_ID}", {"retail_config": rc},
                      extra_headers={"Prefer": "return=minimal"})
        print(f"  ✓ retail_config.catalog_base_url → {BASE_IMG_URL}")


# ═════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═════════════════════════════════════════════════════════════════════════════

HELP = """
Uso:
  python3 generate_previews.py            → todo (imágenes + DB)
  python3 generate_previews.py images     → solo imágenes
  python3 generate_previews.py sync-db    → solo DB
"""

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "--help":
        print(HELP); sys.exit(0)
    if mode in ("all", "images"):
        generate_all_images()
    if mode in ("all", "sync-db"):
        print("▸ Sincronizando productos con la DB...")
        sync_db()
    print("\n✅ Listo.")
