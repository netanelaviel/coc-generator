import io
from datetime import datetime
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

TEMPLATE_PATH = "static/template.pdf"

PAGE_HEIGHT = 841.89  # A4 in points

# --- Exact positions from pdfplumber analysis ---
#
# Date "26/4/26": Calibri-Light 12pt, x=67.1, top=120.7
# Underline line in template: x=51.8..124.1, top=132.1
# Label ":תאריך" starts at x=126.9 — do NOT cover it
#
# Model "DCRP-50RNF": ArialMT 12pt, x=319.2, top=287.1, ends ~x=393
# SKU "6905414":      ArialMT 12pt, x=432.8, top=287.1, ends ~x=480

FONT_SIZE   = 12
FONT_ASCENT = 9.5   # approx ascent for 12pt Arial/Calibri

# Date
DATE_X      = 67.1
DATE_BASE   = PAGE_HEIGHT - 120.7 - FONT_ASCENT   # baseline in reportlab coords

# Template underline is at pdfplumber top=132.1 → need rect to cover it too
DATE_RECT_X = 49
DATE_RECT_Y = PAGE_HEIGHT - 134   # bottom of rect (below the underline)
DATE_RECT_W = 75                   # covers x=49..124, just before label at 126.9
DATE_RECT_H = 18                   # covers from underline up through the text

# Model
MODEL_X     = 319.2
MODEL_BASE  = PAGE_HEIGHT - 287.1 - FONT_ASCENT
MODEL_RECT_X = 317
MODEL_RECT_Y = PAGE_HEIGHT - 300
MODEL_RECT_W = 80
MODEL_RECT_H = 16

# SKU
SKU_X       = 432.8
SKU_BASE    = PAGE_HEIGHT - 287.1 - FONT_ASCENT
SKU_RECT_X  = 430
SKU_RECT_Y  = PAGE_HEIGHT - 300
SKU_RECT_W  = 52
SKU_RECT_H  = 16


# Standards block — fits in the empty gap between body text (top≈393) and signature (top≈471)
STANDARDS_START_Y = PAGE_HEIGHT - 402 - 6   # first baseline in reportlab coords
STANDARDS_LINE_H  = 9.0                      # line spacing in points

STANDARDS_LINES = [
    (True,  "Relevant standards:"),
    (False, "• IEC / DIN EN 60601-1: Medical electrical equipment – General requirements for safety."),
    (False, "• IEC 60364-7-710: Electrical installations of buildings – Requirements for special"),
    (False, "   installations or locations – Medical locations."),
    (False, "• DIN EN 793 (VDE 0750 Part 211): Particular requirements for safety of medical supply units."),
    (False, "• DIN 42801: Potential equalisation leads – Connecting pins."),
    (False, "• DIN 42801 part 2: Potential equalisation leads – Connecting socket."),
]


def _build_overlay(sku: str, model: str, with_standards: bool) -> bytes:
    now = datetime.now()
    date_str = f"{now.day}/{now.month}/{str(now.year)[2:]}"

    overlay_buf = io.BytesIO()
    c = canvas.Canvas(overlay_buf, pagesize=A4)

    def cover(rx, ry, rw, rh):
        c.setFillColorRGB(1, 1, 1)
        c.rect(rx, ry, rw, rh, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)

    c.setFont("Helvetica", FONT_SIZE)

    # Date — also covers the template's underline below the field
    cover(DATE_RECT_X, DATE_RECT_Y, DATE_RECT_W, DATE_RECT_H)
    c.drawString(DATE_X, DATE_BASE, date_str)

    # Model
    cover(MODEL_RECT_X, MODEL_RECT_Y, MODEL_RECT_W, MODEL_RECT_H)
    c.drawString(MODEL_X, MODEL_BASE, model)

    # SKU
    cover(SKU_RECT_X, SKU_RECT_Y, SKU_RECT_W, SKU_RECT_H)
    c.drawString(SKU_X, SKU_BASE, sku)

    if with_standards:
        y = STANDARDS_START_Y
        for bold, line in STANDARDS_LINES:
            c.setFont("Helvetica-Bold" if bold else "Helvetica", 8)
            c.drawString(27, y, line)
            y -= STANDARDS_LINE_H

    c.save()
    overlay_buf.seek(0)
    return overlay_buf.read()


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


def generate_coc(sku: str, model: str) -> bytes:
    return _merge(_build_overlay(sku, model, with_standards=False))


def generate_coc_with_standards(sku: str, model: str) -> bytes:
    return _merge(_build_overlay(sku, model, with_standards=True))
