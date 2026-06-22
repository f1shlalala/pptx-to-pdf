# PPTX to PDF

A fast, self-hosted web app that converts PowerPoint — and most other Office
documents — to PDF, right in the browser. Drag in a stack of files, optionally
merge them into one PDF, shrink or grayscale the output, and download everything
as a zip.

Powered by a **warm LibreOffice instance** (via [unoserver](https://github.com/unoconv/unoserver)),
so conversions don't pay the cold-start cost of spawning LibreOffice on every
request.

<!-- Add a screenshot of the UI here, e.g.: ![Screenshot](docs/screenshot.png) -->

## Features

- **Many input formats** — presentations, documents, and spreadsheets (see the full list below).
- **Bulk conversion** — drop multiple files; each converts independently with its own status.
- **Merge** — combine the converted PDFs into a single document (client-side, via [pdf-lib](https://pdf-lib.js.org/)).
- **Reverse page order** — flip pages within the output.
- **Grayscale** — strip color using Ghostscript, for smaller / print-friendly PDFs.
- **Compress** — re-encode at `ebook` quality to reduce file size (Ghostscript).
- **Download all as a zip** — grab every result at once (client-side, via [JSZip](https://stuk.github.io/jszip/)).
- **50 MB** per-upload limit.

### Supported input formats

| Category      | Extensions                          |
| ------------- | ----------------------------------- |
| Presentations | `.pptx` `.ppt` `.odp` `.ppsx`       |
| Documents     | `.doc` `.docx` `.odt` `.rtf`        |
| Spreadsheets  | `.xls` `.xlsx` `.ods` `.csv`        |

## How it works

```
Browser (index.html)
  │  upload + options (grayscale / compress)
  ▼
Flask  POST /convert
  │
  ├─ unoconvert ──▶ unoserver ──▶ warm LibreOffice  ──┐  (fast path)
  │                                                   ├─▶ PDF
  └─ libreoffice --headless --convert-to pdf  ────────┘  (cold fallback)
  │
  └─ (optional) Ghostscript: grayscale and/or compress
  ▼
PDF returned to the browser
```

- **Conversion engine.** Each request first tries `unoconvert`, which talks to a
  long-running LibreOffice kept warm by `unoserver`. If that's unavailable it
  falls back to spawning a one-off headless LibreOffice. Both paths are bounded
  by a 120s timeout.
- **Post-processing.** When *grayscale* or *compress* is selected, the PDF is run
  through Ghostscript (`-sDEVICE=pdfwrite`); on any Ghostscript failure the
  original PDF is returned unchanged.
- **Merge, reverse, and zip happen in the browser.** The server converts one file
  at a time; combining, reordering, and zipping are done client-side with
  `pdf-lib` and `JSZip`, so the backend stays simple and stateless.
- **Stateless & private.** Uploads are written to a per-request temp directory and
  deleted as soon as the response is sent. Nothing is persisted.

## Tech stack

- **Backend:** Python, [Flask](https://flask.palletsprojects.com/), served by [gunicorn](https://gunicorn.org/)
- **Conversion:** [LibreOffice](https://www.libreoffice.org/) + [unoserver](https://github.com/unoconv/unoserver) (`python3-uno`), [Ghostscript](https://www.ghostscript.com/)
- **Frontend:** vanilla HTML/CSS/JS, [pdf-lib](https://pdf-lib.js.org/), [JSZip](https://stuk.github.io/jszip/) (loaded from CDN)
- **Packaging / deploy:** Docker, [Render](https://render.com/)

## Running locally

The converter needs LibreOffice, Ghostscript, and the `uno` Python bindings, so
the supported way to run it is with Docker — the image wires all of that up for
you.

```bash
# Build
docker build -t pptx-to-pdf .

# Run (the app listens on port 10000 inside the container)
docker run --rm -p 10000:10000 pptx-to-pdf
```

Then open <http://localhost:10000>.

> **Note on startup:** `start.sh` launches `unoserver` and kicks off a background
> prewarm (a throwaway conversion) so the first real request is fast, while
> gunicorn binds the port immediately. The very first conversion right after boot
> may be a little slower until the warmup finishes — the logs print
> `unoserver ready (prewarmed)` when it's done.

### Without Docker

You can run just the Flask app for frontend/UI work, but conversions will fail
unless LibreOffice + unoserver are installed and on your `PATH`:

```bash
pip install -r requirements.txt
python app.py            # serves on http://localhost:5000
```

## API

### `POST /convert`

Convert a single file to PDF.

**Request** — `multipart/form-data`:

| Field       | Type   | Required | Description                                        |
| ----------- | ------ | -------- | -------------------------------------------------- |
| `file`      | file   | yes      | The document to convert (see supported formats).   |
| `grayscale` | string | no       | Truthy (`1`/`true`/`on`/`yes`) to convert to gray. |
| `compress`  | string | no       | Truthy value to compress (`ebook` quality).        |

**Responses:**

- `200` — the PDF, as an attachment (`application/pdf`).
- `400` — no file provided, or unsupported file type.
- `500` — conversion failed (includes a `detail` field).

```bash
curl -X POST http://localhost:10000/convert \
  -F "file=@slides.pptx" \
  -F "compress=true" \
  -o slides.pdf
```

### `GET /health`

Liveness check. Returns `ok` with `200`.

## Project structure

```
.
├── app.py             # Flask app: routes, conversion, Ghostscript post-processing
├── templates/
│   └── index.html     # Single-page UI (drag-drop, queue, merge/reverse/zip)
├── Dockerfile         # LibreOffice + Ghostscript + unoserver image
├── start.sh           # Starts unoserver, prewarms it, launches gunicorn (:10000)
├── requirements.txt   # flask, gunicorn
└── .dockerignore / .gitignore
```

## Deployment

Deployed on **Render** as a Docker web service that auto-deploys on every push to
`main`. Key details Render needs:

- **Runtime:** Docker (detected from the `Dockerfile` — no build/start command needed).
- **Port:** the app listens on `10000` (`EXPOSE 10000` + gunicorn binds it in `start.sh`); Render auto-detects it.
- **Environment variables:** none required.

To deploy your own copy: create a new Web Service on Render, connect this repo,
pick the **Docker** runtime and the **Free** plan, and create it. The
`*.onrender.com` URL is derived from the service name you choose.

## License

No license has been specified yet.
