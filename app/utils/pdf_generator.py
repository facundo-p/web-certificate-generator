from fpdf import FPDF, HTMLMixin
from jinja2 import Template
import os
import unicodedata
import html


def sanitize_for_pdf(text: str) -> str:
    """Strip characters likely to break PDF fonts.

    - Remove leading BOM (\ufeff).
    - Drop control categories except \n, \r, \t.
    - Omit characters outside the Latin‑1 (0–255) range, which is what
      the default Helvetica/Arial font in reportlab/fpdf support.

    This is a best–effort cleanup; if you need accented or non‑Latin
    characters consider registering a Unicode font instead of sanitising.
    """
    if not text:
        return text

    # strip order‑mark that often appears at start of files
    text = text.lstrip("\ufeff")
    out_chars = []

    for ch in text:
        cat = unicodedata.category(ch)
        # keep simple whitespace and line breaks
        if cat.startswith("C") and ch not in "\n\r\t":
            # control/other character; skip it
            continue
        # drop anything outside latin‑1; log to help debugging
        if ord(ch) > 0xFF:
            print(f"sanitize_for_pdf: removing {ch!r} (U+{ord(ch):04X})")
            continue
        out_chars.append(ch)

    return "".join(out_chars)

class PDF(FPDF, HTMLMixin):
    pass


class PdfGenerator:
    def __init__(self, html_template, background_image_path, unicode_font_path: str | None = None, unicode_font_name: str = "Unicode"):
        """
        Initializes the PdfGenerator with a Jinja2 template and a background image path.

        :param html_template: a `jinja2.Template` instance.
        :param background_image_path: path to the certificate background image.
        :param unicode_font_path: optional path to a TrueType font file with Unicode support.
        :param unicode_font_name: name to register the font under (used with ``pdf.set_font``).
        """
        self.html_template = html_template
        self.background_image_path = background_image_path
        self.unicode_font_path = unicode_font_path
        self.unicode_font_name = unicode_font_name

        if not self.background_image_path:
            raise ValueError("Background image path must be provided.")
        if not self.html_template:
            raise ValueError("HTML template must be provided.")
        if not isinstance(self.html_template, Template):
            raise TypeError("html_template must be a Jinja2 Template object.")
        if not isinstance(self.background_image_path, str):
            raise TypeError("background_image_path must be a string representing the file path.")
        if self.unicode_font_path and not isinstance(self.unicode_font_path, str):
            raise TypeError("unicode_font_path must be a string if provided.")
        if not isinstance(self.unicode_font_name, str):
            raise TypeError("unicode_font_name must be a string.")

    def generate_pdf(self, data, output_path):
        """Generates a single PDF certificate."""
        pdf = PDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()

        # Background image
        pdf.image(self.background_image_path, x=0, y=0, w=297, h=210)
        pdf.set_left_margin(60)
        pdf.set_right_margin(60)
        pdf.set_y(78)

        # register a unicode font if requested; FPDF requires a live instance
        if self.unicode_font_path:
            # the ``uni=True`` flag tells FPDF to generate the required
            # font metrics file and to allow the full unicode range.
            try:
                pdf.add_font(self.unicode_font_name, '', self.unicode_font_path, uni=True)
                pdf.set_font(self.unicode_font_name, size=16)
            except Exception as exc:
                # fall back to Arial but bubble a warning for visibility
                print(f"warning: could not add unicode font {self.unicode_font_path}: {exc}")
                pdf.set_font("Arial", size=16)
        else:
            pdf.set_font("Arial", size=16)

        rendered_html = self.html_template.render(data)
        rendered_html = sanitize_for_pdf(rendered_html)
        try:
            pdf.write_html(rendered_html)
        except Exception as e:
            print(f"ERROR in write_html: {e}")
            print(f"Attempted to render: {rendered_html}")
            raise

        pdf.output(output_path)
        return output_path

    def generate_all_pdfs(self, data_list, output_folder, progress_callback=None, channel=None):
        """
        Generates one PDF per data row and reports progress.

        :param data_list: List of dictionaries (rows from CSV).
        :param output_folder: Folder where PDFs will be saved.
        :param progress_callback: Optional function(progress_percent, message)
        :param channel: Optional channel identifier for progress reporting. 
        """
        # Validate that data_list is not empty
        if not data_list:
            raise ValueError("data_list is empty; no PDFs to generate.")
        
        # Validate that 'name' column exists in the first row
        first_row = data_list[0]
        if 'name' not in first_row:
            available_cols = ", ".join(first_row.keys())
            raise KeyError(
                f"CSV must have a 'name' column. Available columns: {available_cols}"
            )
        
        os.makedirs(output_folder, exist_ok=True)
        total = len(data_list)
        pdf_paths = []
        try:
            for i, data in enumerate(data_list, start=1):
                try:
                    output_path = os.path.join(output_folder, f"{data['name']}.pdf")
                    self.generate_pdf(data, output_path)
                    pdf_paths.append(output_path)
                except KeyError as ke:
                    raise KeyError(f"Row {i} has missing key: {ke}")

                # Emit progress
                if progress_callback:
                    percent = int((i / total) * 100)
                    progress_callback(percent, f"Generado {i}/{total} certificados...", channel)
                    
        except Exception as e:
            mensaje = f"No se pudo generar el PDF en la línea {i}: {e}"
            print(mensaje)
            raise Exception(mensaje) from e

        return pdf_paths
