FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libreoffice \
    ghostscript \
    python3-uno \
    python3-pip \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# unoserver keeps one LibreOffice instance warm. It MUST be installed with the
# distro python (/usr/bin/python3) — the one that owns the `uno` bindings from
# python3-uno. The unoserver/unoconvert console scripts then get a
# /usr/bin/python3 shebang so they can import uno. (Installing it with the image's
# /usr/local python fails at runtime with "No module named 'uno'".)
RUN /usr/bin/python3 -m pip install --no-cache-dir --break-system-packages unoserver

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start.sh

EXPOSE 10000

CMD ["./start.sh"]
