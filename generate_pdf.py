import io
from datetime import datetime
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth

TEMPLATE_PATH = "static/template.pdf"
PAGE_HEIGHT   = 841.89  # A4 points

FONT_SIZE     = 12
ASCENT_RATIO  = 0.792   # Helvetica ascent ≈ 79.2% of em

# ── Date field ────────────────────────────────────────────────────────────────
# Calibri-Light 12pt at pdfplumber (67.1, 120.7)
# Template underline at top=132.1, x=51.8..124.1
DATE_X      = 67.1
DATE_BASE   = PAGE_HEIGHT - 120.7 - FONT_SIZE * ASCENT_RATIO
DATE_RECT_X = 49;  DATE_RECT_Y = PAGE_HEIGHT - 134
DATE_RECT_W = 75;  DATE_RECT_H = 18

# ── Single SKU/Model line ─────────────────────────────────────────────────────
# ArialMT 12pt; model at x=319.2, SKU right-aligned to x=478 (before :מ"ק at 482)
LINE_TOP    = 287.1
MODEL_X     = 319.2
SKU_RIGHT_X = 478
LINE_AVAIL  = SKU_RIGHT_X - MODEL_X   # ~158.8 pt

LINE_RECT_X = 317;  LINE_RECT_Y = PAGE_HEIGHT - 301
LINE_RECT_W = 163;  LINE_RECT_H = 17

# ── Multi-SKU area ────────────────────────────────────────────────────────────
# Covers original SKU line + gap + body-text area (pdfplumber top 278..393)
MULTI_TOP_PL   = 278
MULTI_BTM_PL   = 393
MULTI_COVER_Y  = PAGE_HEIGHT - MULTI_BTM_PL          # 448.89  (rl bottom)
MULTI_COVER_H  = (PAGE_HEIGHT - MULTI_TOP_PL) - MULTI_COVER_Y  # ≈ 115 pt

MULTI_HEADER_PL = 284   # pdfplumber top for header row
MULTI_ITEMS_PL  = 297   # pdfplumber top for first item row
MULTI_LINE_H    = 11    # pt per item row (pdfplumber units)
MAX_ITEMS       = 8

# ── Standards block ───────────────────────────────────────────────────────────
# Empty gap between body text (top≈393) and signature (top≈471)
STANDARDS_START_Y = PAGE_HEIGHT - 402 - 6
STANDARDS_LINE_H  = 9.0

STANDARDS_LINES = [
    (True,  "Relevant standards:"),
    (False, "• IEC / DIN EN 60601-1: Medical electrical equipment – General requirements for safety."),
    (False, "• IEC 60364-7-710: Electrical installations of buildings – Requirements for special"),
    (False, "   installations or locations – Medical locations."),
    (False, "• DIN EN 793 (VDE 0750 Part 211): Particular requirements for safety of medical supply units."),
    (False, "• DIN 42801: Potential equalisation leads – Connecting pins."),
    (False, "• DIN 42801 part 2: Potential equalisation leads – Connecting socket."),
]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _rl_base(pl_top, fs):
    """Convert pdfplumber top → reportlab baseline y."""
    return PAGE_HEIGHT - pl_top - fs * ASCENT_RATIO


def _fit_size(model, sku, avail, base=FONT_SIZE, min_size=7.0):
    combined = stringWidth(model, "Helvetica", base) + 8 + stringWidth(sku, "Helvetica", base)
    if combined <= avail:
        return base
    return max(min_size, base * avail / combined)


def _draw_date(c, date_str):
    c.setFillColorRGB(1, 1, 1)
    c.rect(DATE_RECT_X, DATE_RECT_Y, DATE_RECT_W, DATE_RECT_H, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", FONT_SIZE)
    c.drawString(DATE_X, DATE_BASE, date_str)


def _draw_single_item(c, sku, model):
    fs = _fit_size(model, sku, LINE_AVAIL)
    c.setFillColorRGB(1, 1, 1)
    c.rect(LINE_RECT_X, LINE_RECT_Y, LINE_RECT_W, LINE_RECT_H, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", fs)
    base = _rl_base(LINE_TOP, fs)
    c.drawString(MODEL_X, base, model)
    c.drawRightString(SKU_RIGHT_X, base, sku)


def _draw_multi_items(c, items):
    n = len(items)
    fs = FONT_SIZE if n <= 4 else (10 if n <= 6 else 8.5)

    # White cover rect over SKU line + gap + body text
    c.setFillColorRGB(1, 1, 1)
    c.rect(27, MULTI_COVER_Y, 456, MULTI_COVER_H, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)

    # Column headers (small, gray)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.setFont("Helvetica-Bold", 8)
    header_base = _rl_base(MULTI_HEADER_PL, 8)
    c.drawString(MODEL_X, header_base, "Model")
    c.drawRightString(SKU_RIGHT_X, header_base, "SKU")

    # Thin separator line
    sep_y = header_base - 3
    c.setStrokeColorRGB(0.6, 0.6, 0.6)
    c.setLineWidth(0.5)
    c.line(MODEL_X, sep_y, SKU_RIGHT_X, sep_y)

    # Item rows
    c.setFillColorRGB(0, 0, 0)
    for i, (sku, model) in enumerate(items):
        pl_top = MULTI_ITEMS_PL + i * MULTI_LINE_H
        row_fs = _fit_size(model, sku, LINE_AVAIL, fs)
        c.setFont("Helvetica", row_fs)
        base = _rl_base(pl_top, row_fs)
        c.drawString(MODEL_X, base, model)
        c.drawRightString(SKU_RIGHT_X, base, sku)


def _draw_standards(c):
    y = STANDARDS_START_Y
    for bold, line in STANDARDS_LINES:
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 8)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(27, y, line)
        y -= STANDARDS_LINE_H


def _build(items: list, with_standards: bool) -> bytes:
    now = datetime.now()
    date_str = f"{now.day}/{now.month}/{str(now.year)[2:]}"

    buf = io.BytesIO()
    c   = canvas.Canvas(buf, pagesize=A4)

    _draw_date(c, date_str)

    if len(items) == 1:
        _draw_single_item(c, items[0][0], items[0][1])
    else:
        _draw_multi_items(c, items)

    if with_standards:
        _draw_standards(c)

    c.save()
    buf.seek(0)
    return buf.read()


def _merge(overlay_bytes: bytes) -> bytes:
    template = PdfReader(TEMPLATE_PATH)
    overlay  = PdfReader(io.BytesIO(overlay_bytes))
    writer   = PdfWriter()
    page     = template.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()


# ── Public API ────────────────────────────────────────────────────────────────

def generate_coc(items: list) -> bytes:
    """items = [(sku, model), ...]"""
    return _merge(_build(items, with_standards=False))


def generate_coc_with_standards(items: list) -> bytes:
    """items = [(sku, model), ...]"""
    return _merge(_build(items, with_standards=True))
