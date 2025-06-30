from flask import Flask, request, render_template, send_file, jsonify
import os
import csv
from fpdf import FPDF
from jinja2 import Template
import zipfile
from io import BytesIO
from app.utils.pdf_generator import PdfGenerator  # Import the PdfGenerator class

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['GENERATED_FOLDER'] = 'generated'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'csv_file' in request.files and 'html_file' in request.files and 'image_file' in request.files:
        csv_file = request.files['csv_file']
        html_file = request.files['html_file']
        image_file = request.files['image_file']

        # Save files
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'data.csv')
        html_path = os.path.join(app.config['UPLOAD_FOLDER'], 'template.html')
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'background.png')

        csv_file.save(csv_path)
        html_file.save(html_path)
        image_file.save(image_path)

        return jsonify({'message': 'Files uploaded successfully!'}), 200
    return jsonify({'error': 'All files are required!'}), 400

@app.route('/generate', methods=['POST'])
def generate_certificates():
    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], 'data.csv')
    html_path = os.path.join(app.config['UPLOAD_FOLDER'], 'template.html')
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'background.png')

    if not (os.path.exists(csv_path) and os.path.exists(html_path) and os.path.exists(image_path)):
        return jsonify({'error': 'Missing uploaded files!'}), 400

    # Read HTML template
    with open(html_path, 'r') as f:
        html_template = Template(f.read())

    # Create an instance of PdfGenerator
    pdf_generator = PdfGenerator(html_template, image_path)

    # Read CSV and generate PDFs using pdf_generator.py
    pdf_files = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pdf_path = os.path.join(app.config['GENERATED_FOLDER'], f"{row['name']}.pdf")
            pdf_generator.generate_pdf(row, pdf_path)  # Call the method
            pdf_files.append(pdf_path)

    # Create ZIP file
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        for pdf_file in pdf_files:
            zipf.write(pdf_file, os.path.basename(pdf_file))
    zip_buffer.seek(0)

    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='certificates.zip')

if __name__ == '__main__':
    app.run(debug=True)