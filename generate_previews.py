#!/usr/bin/env python3
"""
Generador de imágenes de preview para catálogos En Un Clic.

Uso:
  python3 generate_previews.py             # regenera todos
  python3 generate_previews.py combos      # solo el catálogo de combos
  python3 generate_previews.py fix-dd      # corrige $$ → $ en fichas individuales

Requiere: Pillow  →  pip install Pillow
"""

import os, sys, textwrap
from PIL import Image, ImageDraw, ImageFont

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_DIR   = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD  = "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf"
FONT_REG   = "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"
FONT_BLACK = "/usr/share/fonts/truetype/msttcorefonts/Arial_Black.ttf"

# ── Brand ─────────────────────────────────────────────────────────────────────
GOLD        = (198, 158, 47)
WHITE       = (255, 255, 255)
DARK_TEXT   = (40, 40, 40)
LIGHT_TEXT  = (100, 100, 100)
GOLD_TEXT   = (198, 158, 47)   # price color on white bg
YELLOW_BG   = (253, 213, 102)  # description banner
SEPARATOR   = (220, 210, 180)

W, H = 1080, 1350
WHATSAPP    = "+54 376 541-3840"
FOOTER_LINE = "Entrega en el dia en Posadas • Todo el pais"

# ── Combos — ORDENADOS precio DESC (price anchoring) ─────────────────────────
COMBOS = [
    {
        "name":        "Experiencia Spa Total",
        "description": "Incluye 8 productos: Mousse Limpiadora · Sérum Vit C · Protector Solar · Gel Ducha · Exfoliante · Loción Corporal · Champú · Aceite Capilar",
        "price":       72000,
        "slug":        "experiencia-spa-total",
        "productos":   8,
    },
    {
        "name":        "Piel de Seda Corporal",
        "description": "Incluye: Gel de Ducha Rose 500ml · Exfoliante Melocotón 250g · Loción Niacinamida 250ml",
        "price":       33000,
        "slug":        "piel-seda-corporal",
        "productos":   3,
    },
    {
        "name":        "Melena de Ensueño",
        "description": "Incluye: Champú Anticaspa Romero 500ml · Mascarilla Queratina 500ml · Aceite Reparador Puré de Arroz",
        "price":       30500,
        "slug":        "melena-sueno",
        "productos":   3,
    },
    {
        "name":        "Reparación Nocturna",
        "description": "Incluye: Limpiador Retinol · Sérum Retinol+Cafeína · Crema de Ojos · Crema Colágeno Perla",
        "price":       24500,
        "slug":        "reparacion-nocturna",
        "productos":   4,
    },
    {
        "name":        "Mañana Radiante",
        "description": "Incluye: Limpiador Vitamina C · Sérum Vitamina C 100ml · Protector Solar SPF50+",
        "price":       14500,
        "slug":        "manana-radiante",
        "productos":   3,
    },
    {
        "name":        "Manos de Terciopelo",
        "description": "Incluye: Crema Manos 150g · Crema Bolso 30g · Crema Anti-grietas 60g",
        "price":        9400,
        "slug":        "manos-terciopelo",
        "productos":   3,
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def font(path, size):
    return ImageFont.truetype(path, size)

def centered_text(draw, text, y, font_obj, color, width=W):
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, y), text, font=font_obj, fill=color)

def price_str(p):
    """$72.000  (punto como separador de miles, sin doble $$)"""
    return f"${p:,.0f}".replace(",", ".")

def draw_header(draw, title_line1, title_line2=None, bg_color=GOLD):
    """Gold header con dos líneas de título."""
    draw.rectangle([0, 0, W, 185], fill=bg_color)
    f_brand = font(FONT_BOLD, 48)
    f_title = font(FONT_BLACK, 58) if title_line2 else font(FONT_BOLD, 60)
    centered_text(draw, "En Un Clic", 28, f_brand, WHITE)
    if title_line2:
        centered_text(draw, title_line2, 100, f_title, WHITE)
    else:
        centered_text(draw, title_line1, 85, font(FONT_BOLD, 52), WHITE)

def draw_footer(draw, y_start=H-90):
    draw.rectangle([0, y_start, W, H], fill=GOLD)
    f = font(FONT_BOLD, 34)
    f2 = font(FONT_REG, 26)
    centered_text(draw, f"WhatsApp: {WHATSAPP}", y_start + 14, f, WHITE)
    centered_text(draw, FOOTER_LINE, y_start + 54, f2, WHITE)


# ── 1. preview_combos.jpg ─────────────────────────────────────────────────────

def generate_combos_catalog():
    """Lista de todos los combos ordenados por precio DESC."""
    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([0, 0, W, 185], fill=GOLD)
    centered_text(draw, "En Un Clic",       28,  font(FONT_BOLD, 48),  WHITE)
    centered_text(draw, "Combos Skincare",  100, font(FONT_BLACK, 56), WHITE)

    # Items
    margin_l = 60
    margin_r = 60
    y = 210
    row_h = (H - 90 - 210) // len(COMBOS)   # dynamic row height

    f_name   = font(FONT_BOLD, 36)
    f_desc   = font(FONT_REG,  26)
    f_price  = font(FONT_BLACK, 44)

    for i, combo in enumerate(COMBOS):
        # Product name
        draw.text((margin_l, y + 10), combo["name"], font=f_name, fill=DARK_TEXT)

        # Description (truncated to one line)
        desc_short = combo["description"]
        if len(desc_short) > 62:
            desc_short = desc_short[:59] + "…"
        draw.text((margin_l, y + 54), desc_short, font=f_desc, fill=LIGHT_TEXT)

        # Price (right-aligned)
        p_text = price_str(combo["price"])
        bbox = draw.textbbox((0, 0), p_text, font=f_price)
        pw = bbox[2] - bbox[0]
        draw.text((W - margin_r - pw, y + 22), p_text, font=f_price, fill=GOLD_TEXT)

        # Separator (not after last item)
        if i < len(COMBOS) - 1:
            draw.line([(margin_l, y + row_h - 8), (W - margin_r, y + row_h - 8)],
                      fill=SEPARATOR, width=2)

        y += row_h

    draw_footer(draw)

    out = os.path.join(REPO_DIR, "preview_combos.jpg")
    img.save(out, "JPEG", quality=92)
    print(f"✓ {out}")


# ── 2. Fichas individuales — fix $$ en header ─────────────────────────────────

INDIVIDUAL_HEADER_H = 295   # gold header height (y=0..295)

def fix_individual_header(slug, name, price, n_products):
    """Repinta el header de una ficha individual corrigiendo $$→$."""
    src = os.path.join(REPO_DIR, f"preview_combo-{slug}.jpg")
    if not os.path.exists(src):
        print(f"  ✗ no existe: {src}")
        return

    img = Image.open(src).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Repaint header region
    draw.rectangle([0, 0, W, INDIVIDUAL_HEADER_H], fill=GOLD)

    # "En Un Clic"
    centered_text(draw, "En Un Clic", 30, font(FONT_BOLD, 44), WHITE)
    # Product name
    centered_text(draw, name, 90, font(FONT_BLACK, 52), WHITE)
    # Price — single $
    centered_text(draw, f"{price_str(price)} ARS", 160, font(FONT_BLACK, 52), WHITE)
    # N productos
    centered_text(draw, f"* {n_products} productos incluidos", 228, font(FONT_BOLD, 30), WHITE)

    out = os.path.join(REPO_DIR, f"preview_combo-{slug}.jpg")
    img.save(out, "JPEG", quality=92)
    print(f"✓ {out}")


def fix_all_individual():
    for combo in COMBOS:
        fix_individual_header(
            combo["slug"],
            combo["name"],
            combo["price"],
            combo["productos"],
        )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "combos"):
        print("Generando preview_combos.jpg...")
        generate_combos_catalog()

    if mode in ("all", "fix-dd", "fix"):
        print("Corrigiendo $$ en fichas individuales...")
        fix_all_individual()

    print("\nListo.")
