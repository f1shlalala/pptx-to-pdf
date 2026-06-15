import io
import os
import re
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB limit


def safe_stem(filename: str) -> str:
    return re.sub(r"[^\w\-.]", "_", Path(filename).stem)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".pptx"):
        return jsonify({"error": "Only .pptx files are supported"}), 400

    stem = safe_stem(file.filename)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / f"{stem}.pptx"
        file.save(input_path)

        result = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", tmpdir,
                str(input_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            return jsonify({"error": "Conversion failed", "detail": result.stderr}), 500

        pdf_path = Path(tmpdir) / f"{stem}.pdf"
        if not pdf_path.exists():
            return jsonify({"error": "PDF not generated"}), 500

        pdf_bytes = pdf_path.read_bytes()

    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=f"{stem}.pdf",
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
