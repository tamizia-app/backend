from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _create_watermark_page() -> BytesIO:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 72)
    c.setFillColorRGB(1, 0, 0, alpha=0.4)
    c.saveState()
    c.translate(4.25 * inch, 5.5 * inch)
    c.rotate(45)
    c.drawCentredString(0, 0, "ANULADO")
    c.restoreState()
    c.save()
    buf.seek(0)
    return buf


def watermark_pdf(content: bytes) -> bytes:
    reader = PdfReader(BytesIO(content))
    writer = PdfWriter()
    watermark_buf = _create_watermark_page()
    watermark_reader = PdfReader(watermark_buf)
    watermark_page = watermark_reader.pages[0]

    for page in reader.pages:
        page.merge_page(watermark_page, over=True)
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output.read()
