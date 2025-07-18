FROM python:3.11-slim

WORKDIR /app

# Instala dependências de sistema necessárias para OCR, imagem, PDF, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    poppler-utils \
    tesseract-ocr \
    ghostscript \
    curl \
    wget \
    git \
    unzip \
    bash-completion \
    && rm -rf /var/lib/apt/lists/*

# Copia o requirements e o backend da aplicação
COPY requirements.txt ./requirements.txt
COPY backend/ ./

# Cria ambiente virtual
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instala as dependências do Python no ambiente virtual
RUN pip install --upgrade pip && pip install -r requirements.txt

# Concede permissão total a todos os arquivos e diretórios
RUN chmod -R 777 /app /mnt /opt /workspace || true

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]