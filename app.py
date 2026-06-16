import io
import os
import re
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB limit

# Input formats LibreOffice can convert to PDF
ALLOWED_EXT = {
    ".pptx", ".ppt", ".odp", ".ppsx",
    ".doc", ".docx", ".odt", ".rtf",
    ".xls", ".xlsx", ".ods", ".csv",
}


def safe_stem(filename: str) -> str:
    return re.sub(r"[^\w\-.]", "_", Path(filename).stem)


def truthy(value: str) -> bool:
    return str(value).lower() in ("1", "true", "on", "yes")


def postprocess_pdf(src: Path, dst: Path, grayscale: bool, compress: bool) -> bool:
    """Run Ghostscript to grayscale and/or compress a PDF. Returns True on success."""
    args = [
        "gs", "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", "-dQUIET",
        "-dCompatibilityLevel=1.5",
        "-dPDFSETTINGS=/ebook" if compress else "-dPDFSETTINGS=/default",
    ]
    if grayscale:
        args += [
            "-sColorConversionStrategy=Gray",
            "-sProcessColorModel=DeviceGray",
            "-dOverrideICC",
        ]
    args += [f"-sOutputFile={dst}", str(src)]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("Ghostscript failed to run: %s", exc)
        return False
    if result.returncode != 0 or not dst.exists():
        app.logger.warning("Ghostscript error: %s", result.stderr)
        return False
    return True


def convert_to_pdf(input_path: Path, pdf_path: Path, tmpdir: Path) -> tuple[bool, str]:
    """Convert to PDF via the warm unoserver; fall back to a cold LibreOffice spawn."""
    # Fast path: reuse the already-running LibreOffice via unoserver.
    try:
        r = subprocess.run(
            ["unoconvert", "--convert-to", "pdf", str(input_path), str(pdf_path)],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0 and pdf_path.exists():
            return True, ""
        app.logger.warning("unoconvert miss (rc=%s): %s", r.returncode, r.stderr)
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("unoconvert unavailable: %s", exc)

    # Fallback: cold LibreOffice (writes {stem}.pdf into tmpdir).
    r = subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmpdir), str(input_path)],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        return False, r.stderr
    if not pdf_path.exists():
        return False, "PDF not generated"
    return True, ""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return "ok", 200


@app.route("/convert", methods=["POST"])
def convert():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if not file.filename or ext not in ALLOWED_EXT:
        return jsonify({"error": "Unsupported file type"}), 400

    grayscale = truthy(request.form.get("grayscale", ""))
    compress = truthy(request.form.get("compress", ""))

    stem = safe_stem(file.filename)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / f"{stem}{ext}"
        file.save(input_path)
        pdf_path = Path(tmpdir) / f"{stem}.pdf"

        ok, detail = convert_to_pdf(input_path, pdf_path, Path(tmpdir))
        if not ok:
            return jsonify({"error": "Conversion failed", "detail": detail}), 500

        if grayscale or compress:
            gs_path = Path(tmpdir) / f"{stem}_gs.pdf"
            if postprocess_pdf(pdf_path, gs_path, grayscale, compress):
                pdf_path = gs_path  # fall back to original on failure

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
