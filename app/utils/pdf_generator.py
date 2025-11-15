from fpdf import FPDF, HTMLMixin
from jinja2 import Template
import os

class PDF(FPDF, HTMLMixin):
    pass


class PdfGenerator:
    def __init__(self, html_template, background_image_path):
        """
        Initializes the PdfGenerator with a Jinja2 template and a background image path.
        """
        self.html_template = html_template
        self.background_image_path = background_image_path

        if not self.background_image_path:
            raise ValueError("Background image path must be provided.")
        if not self.html_template:
            raise ValueError("HTML template must be provided.")
        if not isinstance(self.html_template, Template):
            raise TypeError("html_template must be a Jinja2 Template object.")
        if not isinstance(self.background_image_path, str):
            raise TypeError("background_image_path must be a string representing the file path.")

    def generate_pdf(self, data, output_path):
        """Generates a single PDF certificate."""
        pdf = PDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()

        # Background image
        pdf.image(self.background_image_path, x=0, y=0, w=297, h=210)
        pdf.set_left_margin(60)
        pdf.set_right_margin(60)
        pdf.set_y(78)

        # Render HTML
        pdf.set_font("Arial", size=16)
        rendered_html = self.html_template.render(data)
        pdf.write_html(rendered_html)

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
        os.makedirs(output_folder, exist_ok=True)
        total = len(data_list)
        pdf_paths = []
        try:
            for i, data in enumerate(data_list, start=1):
                output_path = os.path.join(output_folder, f"{data['name']}.pdf")
                self.generate_pdf(data, output_path)
                pdf_paths.append(output_path)

                # Emit progress
                if progress_callback:
                    percent = int((i / total) * 100)
                    progress_callback(percent, f"Generado {i}/{total} certificados...", channel)
        except Exception as e:
            mensaje = f"No se pudo generar el PDF en la línea {i}: {e}"
            raise Exception(mensaje) from e

        return pdf_paths
