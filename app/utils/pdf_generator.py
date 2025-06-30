from fpdf import FPDF
from jinja2 import Template
from fpdf import FPDF, HTMLMixin

class PDF(FPDF, HTMLMixin):
    pass

class PdfGenerator:
    def __init__(self, html_template, background_image_path):
        """
        Initializes the PdfGenerator with a Jinja2 template and a background image path.

        :param
        html_template: Jinja2 Template object for rendering the certificate content.
        :param background_image_path: Path to the background image file.
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
        """
        Generates a PDF certificate.

        :param data: Dictionary containing the data for the certificate (e.g., a row from the CSV).
        :param html_template: Jinja2 Template object for rendering the certificate content.
        :param background_image: Path to the background image file.
        :param output_path: Path to save the generated PDF.
        """
        # Create a PDF instance
        pdf = PDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()

        # Add the background image
        pdf.image(self.background_image_path, x=0, y=0, w=297, h=210)  
        # Center the HTML content on the page
        pdf.set_left_margin(60)  # Set left margin
        pdf.set_right_margin(60)  # Set right margin
        pdf.set_y(78)  # Adjust vertical position (top margin)

        # Add the rendered HTML content to the PDF
        pdf.set_font("Arial", size=16)
        rendered_html = self.html_template.render(data)
        pdf.write_html(rendered_html)
        
        pdf.output(output_path)