import io
from datetime import datetime
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

TEMPLATE_PATH = "static/template.pdf"

# Positions measured from the original PDF (pdfplumber top-left origin)
# Converted to reportlab bottom-left origin: y_rl = page_height - y_pl
PAGE_HEIGHT = 841.89

# Date field: "26/4/26" at pdfplumber (67, 121)
DATE_X = 67
DATE_Y_RL = PAGE_HEIGHT - 121   # ~720

# Model field: "DCRP-50RNF" at pdfplumber (319, 287)
MODEL_X = 319
MODEL_Y_RL = PAGE_HEIGHT - 287  # ~554

# SKU field: "6905414" at pdfplumber (433, 287)
SKU_X = 433
SKU_Y_RL = PAGE_HEIGHT - 287    # ~554


def generate_coc(sku: str, model: str) -> bytes:
    now = datetime.now()
    date_str = f"{now.day}/{now.month}/{str(now.year)[2:]}"

    overlay_buf = io.BytesIO()
    c = canvas.Canvas(overlay_buf, pagesize=A4)
    c.setFont("Helvetica", 11)

    def white_rect(x, y, w, h):
        c.setFillColorRGB(1, 1, 1)
        c.rect(x - 2, y - 13, w, 17, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)

    # Replace date
    white_rect(DATE_X, DATE_Y_RL, 85, 17)
    c.drawString(DATE_X, DATE_Y_RL - 2, date_str)

    # Replace model
    white_rect(MODEL_X, MODEL_Y_RL, 110, 17)
    c.drawString(MODEL_X, MODEL_Y_RL - 2, model)

    # Replace SKU
    white_rect(SKU_X, SKU_Y_RL, 55, 17)
    c.drawString(SKU_X, SKU_Y_RL - 2, sku)

    c.save()
    overlay_buf.seek(0)

    template = PdfReader(TEMPLATE_PATH)
    overlay = PdfReader(overlay_buf)

    writer = PdfWriter()
    page = template.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()
