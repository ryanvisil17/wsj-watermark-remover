FROM python:3.14-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        pdftk \
        qpdf \
        poppler-utils && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pikepdf && \
    mkdir /app /workspace

COPY main.py /app/main.py

WORKDIR /workspace

ENTRYPOINT ["python", "/app/main.py"]
CMD []

# Usage:
#   linux:   docker run --rm -u "$(id -u)":"$(id -g)" -v ./:/workspace ryanvisil17/wsj-watermark-remover:latest input.pdf output.pdf
#   windows: docker run --rm -v ${PWD}:/workspace ryanvisil17/wsj-watermark-remover:latest input.pdf output.pdf
