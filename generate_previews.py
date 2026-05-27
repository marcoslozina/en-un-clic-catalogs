#!/usr/bin/env python3
"""
Generador y sincronizador de catálogos — En Un Clic
====================================================

WORKFLOW:
  1. Editá los datos en COMBOS o PRODUCTOS_INDIVIDUALES abajo
  2. Corré: python3 generate_previews.py
  3. Hacé push al repo

Comandos:
  python3 generate_previews.py              # imágenes + sync DB (todo)
  python3 generate_previews.py images       # solo regenera imágenes
  python3 generate_previews.py sync-db      # solo sincroniza la DB
  python3 generate_previews.py combos       # solo imagen preview_combos.jpg
  python3 generate_previews.py fix-headers  # solo repinta headers de fichas individuales

Requiere:
  pip install Pillow
  Variables de entorno (requeridas para sync-db):
    SUPABASE_URL   — URL del proyecto Supabase
    SUPABASE_KEY   — service_role key (NUNCA commitear este valor)
    TENANT_ID      — UUID del tenant en Botly

"""

import os, sys, json, urllib.request
from PIL import Image, ImageDraw, ImageFont

# ── Config DB — solo desde variables de entorno, nunca hardcodeado ────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
TENANT_ID    = os.getenv("TENANT_ID",    "")
BASE_IMG_URL = "https://raw.githubusercontent.com/marcoslozina/en-un-clic-catalogs/main"

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_DIR   = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD  = "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf"
FONT_REG   = "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"
FONT_BLACK = "/usr/share/fonts/truetype/msttcorefonts/Arial_Black.ttf"

# ── Brand ─────────────────────────────────────────────────────────────────────
GOLD       = (198, 158, 47)
WHITE      = (255, 255, 255)
DARK_TEXT  = (40, 40, 40)
LIGHT_TEXT = (100, 100, 100)
GOLD_TEXT  = (198, 158, 47)
SEPARATOR  = (220, 210, 180)
W, H       = 1080, 1350
WHATSAPP   = "+54 376 541-3840"
FOOTER_TXT = "Entrega en el dia en Posadas • Todo el pais"

# ═════════════════════════════════════════════════════════════════════════════
#  FUENTE DE VERDAD — editá estos datos para actualizar precios / productos
# ═════════════════════════════════════════════════════════════════════════════

# COMBOS — ordenados precio DESC (el script mantiene ese orden automáticamente)
COMBOS = [
    {
        "name":        "Experiencia Spa Total",
        "description": "Incluye 8 productos: Mousse Limpiadora · Sérum Vit C · Protector Solar · Gel Ducha · Exfoliante · Loción Corporal · Champú · Aceite Capilar",
        "price":       72000,
        "slug":        "experiencia-spa-total",
        "productos":   8,
        "stock":       30,
    },
    {
        "name":        "Piel de Seda Corporal",
        "description": "Incluye: Gel de Ducha Rose 500ml · Exfoliante Melocotón 250g · Loción Niacinamida 250ml",
        "price":       33000,
        "slug":        "piel-seda-corporal",
        "productos":   3,
        "stock":       50,
    },
    {
        "name":        "Melena de Ensueño",
        "description": "Incluye: Champú Anticaspa Romero 500ml · Mascarilla Queratina 500ml · Aceite Reparador Puré de Arroz",
        "price":       30500,
        "slug":        "melena-sueno",
        "productos":   3,
        "stock":       50,
    },
    {
        "name":        "Reparación Nocturna",
        "description": "Incluye: Limpiador Retinol · Sérum Retinol+Cafeína · Crema de Ojos · Crema Colágeno Perla",
        "price":       24500,
        "slug":        "reparacion-nocturna",
        "productos":   4,
        "stock":       50,
    },
    {
        "name":        "Mañana Radiante",
        "description": "Incluye: Limpiador Vitamina C · Sérum Vitamina C 100ml · Protector Solar SPF50+",
        "price":       14500,
        "slug":        "manana-radiante",
        "productos":   3,
        "stock":       50,
    },
    {
        "name":        "Manos de Terciopelo",
        "description": "Incluye: Crema Manos 150g · Crema Bolso 30g · Crema Anti-grietas 60g",
        "price":        9400,
        "slug":        "manos-terciopelo",
        "productos":   3,
        "stock":       50,
    },
]

# PRODUCTOS INDIVIDUALES por categoría — precio DESC dentro de cada una
PRODUCTOS_INDIVIDUALES = {
    "cara": [
        {"name": "Crema Reparadora Perla",      "sku": "cara-crema-perla",       "price": 11000, "description": "Colágeno SADOER 70g",             "stock": 30},
        {"name": "Mousse Limpiadora Puré",       "sku": "cara-mousse-limpiadora", "price":  7700, "description": "de Arroz BIOAQUA 120ml",           "stock": 40},
        {"name": "Sérum Vitamina C SADOER",      "sku": "cara-serum-vit-c",       "price":  7300, "description": "100ml",                            "stock": 40},
        {"name": "Limpiador Reafirmante",        "sku": "cara-limpiador-retinol", "price":  6300, "description": "Retinol BIOAQUA 100g",             "stock": 40},
        {"name": "Crema de Ojos Cafeína",        "sku": "cara-crema-ojos",        "price":  4300, "description": "Antiarrugas SADOER 20g",           "stock": 40},
        {"name": "Limpiador Iluminador C",       "sku": "cara-limpiador-vitc",    "price":  3800, "description": "Vitamina SADOER",                  "stock": 40},
        {"name": "Protector Solar Puré",         "sku": "cara-protector-solar",   "price":  3500, "description": "de Arroz BIOAQUA SPF50+",          "stock": 40},
        {"name": "Sérum Antiarrugas + Cafeína",  "sku": "cara-serum-retinol",     "price":  2900, "description": "Retinol Cafeína SADOER 30ml",      "stock": 40},
    ],
    "cuerpo": [
        {"name": "Gel de Ducha Rose",            "sku": "cuerpo-gel-ducha",       "price": 15000, "description": "Boquanya 500ml",                  "stock": 40},
        {"name": "Loción Corporal SADOER",       "sku": "cuerpo-locion",          "price": 10500, "description": "Niacinamida Blanqueadora 250ml",  "stock": 40},
        {"name": "Exfoliante Rejuvenecedor",     "sku": "cuerpo-exfoliante",      "price":  7800, "description": "Melocotón Boquanya 250g",          "stock": 40},
    ],
    "manos": [
        {"name": "Crema de Manos Naranja",       "sku": "manos-crema-naranja",    "price":  6300, "description": "VC Vaselina SADOER 150g",          "stock": 40},
        {"name": "Crema Anti-Agrietadas",        "sku": "manos-anti-agrietadas",  "price":  2100, "description": "Manos y Pies SADOER 60g",          "stock": 40},
        {"name": "Crema Manos Niacinamida",      "sku": "manos-crema-niaci",      "price":  1100, "description": "Radiante SADOER 30g",              "stock": 40},
    ],
    "capilar": [
        {"name": "Champú Anticaspa Romero",      "sku": "capilar-champu",         "price": 13500, "description": "SADOER 500ml",                    "stock": 40},
        {"name": "Mascarilla Reparadora",        "sku": "capilar-mascarilla",     "price": 11500, "description": "Queratina SADOER 500ml",           "stock": 40},
        {"name": "Aceite Reparador Cabello",     "sku": "capilar-aceite",         "price":  6100, "description": "Puré de Arroz BIOAQUA 70ml",       "stock": 40},
    ],
}

# ═════════════════════════════════════════════════════════════════════════════
#  Generación de imágenes
# ═════════════════════════════════════════════════════════════════════════════

def fnt(path, size):
    return ImageFont.truetype(path, size)

def centered_text(draw, text, y, font_obj, color, width=W):
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, y), text, font=font_obj, fill=color)

def price_str(p):
    """$72.000  (punto como miles, sin doble $$)"""
    return f"${p:,.0f}".replace(",", ".")

def draw_footer(draw, y_start=H - 90):
    draw.rectangle([0, y_start, W, H], fill=GOLD)
    centered_text(draw, f"WhatsApp: {WHATSAPP}", y_start + 14, fnt(FONT_BOLD, 34), WHITE)
    centered_text(draw, FOOTER_TXT,               y_start + 54, fnt(FONT_REG,  26), WHITE)


def generate_combos_catalog():
    """preview_combos.jpg — lista ordenada precio DESC."""
    combos = sorted(COMBOS, key=lambda c: -c["price"])
    img  = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([0, 0, W, 185], fill=GOLD)
    centered_text(draw, "En Un Clic",      28,  fnt(FONT_BOLD, 48),  WHITE)
    centered_text(draw, "Combos Skincare", 100, fnt(FONT_BLACK, 56), WHITE)

    margin_l = 60
    margin_r = 60
    y      = 210
    row_h  = (H - 90 - 210) // len(combos)
    f_name  = fnt(FONT_BOLD,  36)
    f_desc  = fnt(FONT_REG,   26)
    f_price = fnt(FONT_BLACK, 44)

    for i, combo in enumerate(combos):
        draw.text((margin_l, y + 10), combo["name"], font=f_name, fill=DARK_TEXT)

        desc = combo["description"]
        if len(desc) > 62:
            desc = desc[:59] + "…"
        draw.text((margin_l, y + 54), desc, font=f_desc, fill=LIGHT_TEXT)

        p_text = price_str(combo["price"])
        bbox   = draw.textbbox((0, 0), p_text, font=f_price)
        pw     = bbox[2] - bbox[0]
        draw.text((W - margin_r - pw, y + 22), p_text, font=f_price, fill=GOLD_TEXT)

        if i < len(combos) - 1:
            draw.line([(margin_l, y + row_h - 8), (W - margin_r, y + row_h - 8)],
                      fill=SEPARATOR, width=2)
        y += row_h

    draw_footer(draw)
    out = os.path.join(REPO_DIR, "preview_combos.jpg")
    img.save(out, "JPEG", quality=92)
    print(f"  ✓ {os.path.basename(out)}")


def fix_individual_headers():
    """Repinta el header de cada ficha individual (corrige $$ y mantiene fotos)."""
    HEADER_H = 295
    for combo in COMBOS:
        path = os.path.join(REPO_DIR, f"preview_combo-{combo['slug']}.jpg")
        if not os.path.exists(path):
            print(f"  ✗ no existe: preview_combo-{combo['slug']}.jpg  (saltando)")
            continue
        img  = Image.open(path).convert("RGB")
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, W, HEADER_H], fill=GOLD)
        centered_text(draw, "En Un Clic",                          30,  fnt(FONT_BOLD,  44), WHITE)
        centered_text(draw, combo["name"],                          90,  fnt(FONT_BLACK, 52), WHITE)
        centered_text(draw, f"{price_str(combo['price'])} ARS",   160,  fnt(FONT_BLACK, 52), WHITE)
        centered_text(draw, f"* {combo['productos']} productos incluidos", 228, fnt(FONT_BOLD, 30), WHITE)

        img.save(path, "JPEG", quality=92)
        print(f"  ✓ preview_combo-{combo['slug']}.jpg")


# ═════════════════════════════════════════════════════════════════════════════
#  Sync DB
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
        print("    Exportalas antes de correr sync-db:")
        for v in missing:
            print(f"      export {v}=...")
        sys.exit(1)

    rows = []

    # Combos
    for c in COMBOS:
        rows.append({
            "tenant_id":   TENANT_ID,
            "sku":         f"combo-{c['slug']}",
            "name":        c["name"],
            "description": c["description"],
            "category":    "combos",
            "price":       c["price"],
            "currency":    "ARS",
            "stock":       c["stock"],
            "stock_min":   3,
            "active":      True,
            "metadata":    {
                "image_url": f"{BASE_IMG_URL}/preview_combo-{c['slug']}.jpg",
                "n_products": c["productos"],
            },
        })

    # Individuales
    for cat, products in PRODUCTOS_INDIVIDUALES.items():
        for p in products:
            rows.append({
                "tenant_id":   TENANT_ID,
                "sku":         p["sku"],
                "name":        p["name"],
                "description": p["description"],
                "category":    cat,
                "price":       p["price"],
                "currency":    "ARS",
                "stock":       p["stock"],
                "stock_min":   5,
                "active":      True,
                "metadata":    {},
            })

    # Antes de upsertar, eliminar stale duplicates:
    # si existe un producto con el mismo name+category pero distinto sku, lo borramos
    # para evitar que cambios de SKU entre runs generen duplicados en el catálogo.
    incoming_by_key = {(r["category"], r["name"]): r["sku"] for r in rows}
    existing = _supabase_req("GET", f"products?tenant_id=eq.{TENANT_ID}&select=id,sku,name,category")
    stale_ids = [
        p["id"]
        for p in existing
        if (p["category"], p["name"]) in incoming_by_key
        and p["sku"] != incoming_by_key[(p["category"], p["name"])]
    ]
    if stale_ids:
        id_filter = ",".join(stale_ids)
        _supabase_req("DELETE", f"products?id=in.({id_filter})&tenant_id=eq.{TENANT_ID}", body=None)
        print(f"  ⚠ {len(stale_ids)} producto(s) obsoleto(s) eliminados (SKU cambió)")

    result = _supabase_req("POST", "products?on_conflict=tenant_id,sku", rows)
    print(f"  ✓ {len(result)} productos upserted en DB")

    # Resumen por categoría
    from collections import Counter
    cats = Counter(r["category"] for r in result)
    for cat, n in sorted(cats.items()):
        print(f"    [{cat:10s}] {n} productos")


# ═════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═════════════════════════════════════════════════════════════════════════════

HELP = """
Uso:
  python3 generate_previews.py              → todo (imágenes + DB)
  python3 generate_previews.py images       → solo imágenes
  python3 generate_previews.py sync-db      → solo DB
  python3 generate_previews.py combos       → solo preview_combos.jpg
  python3 generate_previews.py fix-headers  → solo headers de fichas individuales
"""

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "--help":
        print(HELP); sys.exit(0)

    if mode in ("all", "images", "combos"):
        print("▸ Generando preview_combos.jpg...")
        generate_combos_catalog()

    if mode in ("all", "images", "fix-headers"):
        print("▸ Regenerando headers de fichas individuales...")
        fix_individual_headers()

    if mode in ("all", "sync-db"):
        print("▸ Sincronizando productos con la DB...")
        sync_db()

    print("\n✅ Listo.")
