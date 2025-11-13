from flask import Flask, render_template, Response, request, jsonify, send_from_directory
import redis, json, os
from jinja2 import Template
import threading, time, os, zipfile, csv

from utils.pdf_generator import PdfGenerator

app = Flask(
    __name__,
    template_folder=os.path.join('templates'),
    static_folder=os.path.join('static')
)

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

OUTPUT_FOLDER = os.path.join(app.static_folder, 'generated')
TMP_FOLDER = os.path.join(app.static_folder, 'tmp')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TMP_FOLDER, exist_ok=True)


def parse_csv(csv_path):
    """
    Lee un CSV y devuelve una lista de diccionarios (una por fila).
    Ejemplo de estructura: [{'nombre': 'Juan', 'curso': 'Python'}, ...]
    """
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def create_zip(pdf_paths, output_zip_name):
    """
    Crea un ZIP con todos los PDFs generados.
    """
    zip_path = os.path.join(OUTPUT_FOLDER, output_zip_name)
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for pdf in pdf_paths:
            zipf.write(pdf, os.path.basename(pdf))
    return zip_path


def progress_callback(progress, message, channel, download_url=None):
    """
    Envía mensajes al front vía SSE para indicar el progreso al procesar los PDFs.

    :param progress: Porcentaje del trabajo completado.
    :param message: Mensaje a ser mostrado junto a la barra de progreso.
    :param channel: Identificador del canal en el que se estableció la conexión SSE.
    :param download_url: URL para descargar el ZIP final (opcional).
    """
    # Ajustamos el porcentaje total para incluir pasos previos y ZIP final
    adjusted_progress = 10 + int(progress * 0.8)  # de 10% a 90%
    data = {
        "progress": adjusted_progress,
        "message": message,
        "download_url": download_url
    }

    r.publish(channel,json.dumps(data))

def generate_pdfs(csv_path, html_path, bg_img_path, output_zip_name, job_id, app):
    """
    Función que corre en un thread: genera los PDFs y publica progreso vía SSE,
    aprovechando el progress_callback en PdfGenerator.
    """
    with app.app_context():
        try:
            progress_callback(5, "Cargando datos...", job_id)
            data_list = parse_csv(csv_path)
            
            progress_callback(10,"Preparando plantilla...", job_id)
            with open(html_path, "r", encoding="utf-8") as f:
                html_template = Template(f.read())

            pdf_gen = PdfGenerator(html_template, bg_img_path)

            progress_callback(15,"Generando certificados...", job_id)

            pdf_paths = pdf_gen.generate_all_pdfs(
                data_list,
                output_folder=TMP_FOLDER,
                progress_callback=progress_callback,
                channel=job_id
            )

            progress_callback(90, "Creando archivo ZIP...", job_id)
            zip_path = create_zip(pdf_paths, output_zip_name)

            progress_callback(100, "✅ Certificados listos", job_id, f"/download/{output_zip_name}")

            # Limpieza opcional
            for pdf in pdf_paths:
                os.remove(pdf)

        except Exception as e:
            progress_callback(0, f"❌ Error: {e}", job_id)


@app.route('/')
def index():
    print("Index requested")
    return render_template('index.html')

# --- Ruta SSE: /stream ---
@app.route('/stream')
def stream():
    """Abre una conexión SSE que escucha los mensajes de Redis"""
    channel = request.args.get("channel", "events")  # canal por defecto
    
    print(f"✅ el channel es {channel}")

    def event_stream():
        pubsub = r.pubsub()
        pubsub.subscribe(channel)
        for message in pubsub.listen():
            if message['type'] == 'message':
                data = message['data']
                yield f"data: {data}\n\n"

    return Response(event_stream(), mimetype="text/event-stream")


@app.route('/generate', methods=['POST'])
def generate():
    if not ('csv_file' in request.files and 'html_file' in request.files and 'image_file' in request.files):
        return jsonify({'error': 'Se requieren todos los archivos!'}), 400
    
    csv_file = request.files['csv_file']
    html_file = request.files['html_file']
    bg_img = request.files['image_file']

    os.makedirs('tmp', exist_ok=True)
    csv_path = os.path.join('tmp', csv_file.filename)
    html_path = os.path.join('tmp', html_file.filename)
    img_path = os.path.join('tmp', bg_img.filename)

    csv_file.save(csv_path)
    html_file.save(html_path)
    bg_img.save(img_path)

    output_zip_name = f"certificados_{int(time.time())}.zip"
    job_id = f"job_{int(time.time())}"

    threading.Thread(
        target=generate_pdfs,
        args=(csv_path, html_path, img_path, output_zip_name, job_id, app),
        daemon=True
    ).start()

    return jsonify({
        "status": "processing",
        "job_id": job_id
    })


@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

@app.route("/test_sse")
def test_sse():
    progress_callback(42, "Hello from test", "test")
    return "Sent!"


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

