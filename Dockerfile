FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libreoffice \
    ghostscript \
    python3-uno \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# unoserver keeps one LibreOffice instance warm; install it into the system
# python that owns the UNO bindings (python3-uno), not the app's python.
RUN python3 -m pip install --no-cache-dir --break-system-packages unoserver

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start.sh

EXPOSE 10000

CMD ["./start.sh"]
