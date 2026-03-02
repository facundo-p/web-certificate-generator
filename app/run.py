from flask import Flask, render_template, Response, request, jsonify, send_from_directory
import os
from jinja2 import Template
import threading, time, zipfile, csv

from utils.pdf_generator import PdfGenerator
from utils.sse_manager import SSEManager

app = Flask(
    __name__,
    template_folder=os.path.join('templates'),
    static_folder=os.path.join('static')
)

sse_manager = SSEManager()

OUTPUT_FOLDER = os.path.join(app.static_folder, 'generated')
TMP_FOLDER = os.path.join(app.static_folder, 'tmp')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TMP_FOLDER, exist_ok=True)


def parse_csv(csv_path):
    """
    Lee un CSV y devuelve una lista de diccionarios (una por fila).
    Detecta automáticamente el delimitador (coma, punto y coma, tabulador, etc.)
    Ejemplo de estructura: [{'nombre': 'Juan', 'curso': 'Python'}, ...]
    """
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        # Detectar el delimitador automáticamente
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
        except csv.Error:
            # Si Sniffer falla, usar coma como default
            dialect = 'excel'
        
        reader = csv.DictReader(f, dialect=dialect)
        data = [row for row in reader]
        
        # Strip whitespace from keys and values to normalize
        normalized_data = []
        for row in data:
            normalized_row = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
            normalized_data.append(normalized_row)
        
        return normalized_data


def create_zip(pdf_paths, output_zip_name):
    """
    Crea un ZIP con todos los PDFs generados.
    """
    zip_path = os.path.join(OUTPUT_FOLDER, output_zip_name)
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for pdf in pdf_paths:
            zipf.write(pdf, os.path.basename(pdf))
    return zip_path


def generate_pdfs(csv_path, html_path, bg_img_path, output_zip_name, job_id):
    """
    Background task to generate PDFs and send progress updates via SSEManager.
    """
    with app.app_context():
        try:
            sse_manager.progress_callback(1, "Cargando datos...", job_id)
            data_list = parse_csv(csv_path)
            sse_manager.progress_callback(2, "Preparando plantilla...", job_id)

            with open(html_path, "r", encoding="utf-8") as f:
                html_template = Template(f.read())

            pdf_gen = PdfGenerator(html_template, bg_img_path)
            sse_manager.progress_callback(3, "Generando certificados...", job_id)

            pdf_paths = pdf_gen.generate_all_pdfs(
                data_list,
                output_folder=TMP_FOLDER,
                progress_callback=sse_manager.progress_callback,
                channel=job_id
            )

            sse_manager.publish_progress(90, "Creando archivo ZIP...", job_id)
            create_zip(pdf_paths, output_zip_name)
            sse_manager.publish_progress(100, "✅ Certificados listos", job_id, f"/download/{output_zip_name}")

        except Exception as e:
            sse_manager.progress_callback(0, f"❌ Error: {e}", job_id)

        finally:
            # Clean up the SSE channel
            sse_manager.delete_channel(job_id)


@app.route('/')
def index():
    print("Index requested")
    return render_template('index.html')


@app.route('/stream/<job_id>')
def stream(job_id):
    """
    SSE endpoint to stream progress updates for a specific job_id.
    """
    return sse_manager.stream(job_id)


@app.route('/generate', methods=['POST'])
def generate():
    """
    Start a background job to generate PDFs and stream progress updates to the client.
    """
    if not ('csv_file' in request.files and 'html_file' in request.files and 'image_file' in request.files):
        return jsonify({'error': 'All files are required!'}), 400

    # Save uploaded files
    csv_file = request.files['csv_file']
    html_file = request.files['html_file']
    bg_img = request.files['image_file']

    csv_path = os.path.join(TMP_FOLDER, csv_file.filename)
    html_path = os.path.join(TMP_FOLDER, html_file.filename)
    img_path = os.path.join(TMP_FOLDER, bg_img.filename)

    csv_file.save(csv_path)
    html_file.save(html_path)
    bg_img.save(img_path)

    # Generate unique job ID and output ZIP name
    job_id = f"job_{int(time.time())}"
    output_zip_name = f"certificados_{int(time.time())}.zip"

    sse_manager.create_channel(job_id)

    # Start the background task in a separate thread
    threading.Thread(
        target=generate_pdfs,
        args=(csv_path, html_path, img_path, output_zip_name, job_id),
        daemon=True
    ).start()

    return jsonify({
        "status": "processing",
        "job_id": job_id
    })


@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

