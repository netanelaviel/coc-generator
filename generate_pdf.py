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


def generate_coc(sku: str, model: str) -> bytes:
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

    c.save()
    overlay_buf.seek(0)

    template = PdfReader(TEMPLATE_PATH)
    overlay   = PdfReader(overlay_buf)

    writer = PdfWriter()
    page   = template.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()
