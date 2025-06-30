from flask import Blueprint, render_template, request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from src.utils.pdf_generator import PdfGenerator
from jinja2 import Environment, FileSystemLoader

main = Blueprint('main', __name__)

@main.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Handle file uploads
        csv_file = request.files.get("csv_file")
        template_file = request.files.get("template_file")
        image_file = request.files.get("image_file")

        if not csv_file or not template_file or not image_file:
            flash("Please upload all required files.", "error")
            return redirect(url_for("main.index"))

        # Save uploaded files
        upload_folder = "src/uploads"
        os.makedirs(upload_folder, exist_ok=True)

        csv_path = os.path.join(upload_folder, secure_filename(csv_file.filename))
        template_path = os.path.join(upload_folder, secure_filename(template_file.filename))
        image_path = os.path.join(upload_folder, secure_filename(image_file.filename))

        csv_file.save(csv_path)
        template_file.save(template_path)
        image_file.save(image_path)

        # Generate PDFs
        output_folder = os.path.join(upload_folder, "certificates")
        os.makedirs(output_folder, exist_ok=True)

        env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
        pdf_generator = PdfGenerator(env, output_folder, os.path.basename(template_path), image_path)
        pdf_generator.generate_pdfs(csv_path)

        flash("PDFs generated successfully!", "success")
        return redirect(url_for("main.index"))

    return render_template("index.html")