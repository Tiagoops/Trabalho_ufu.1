FROM python:3.12.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py banco_dados.py modelos.py tipos.py cores.py migracao.py servico_risco.py avaliacao.py biblioteca.py catalogo_cvss.py ./
COPY matematica/ ./matematica/
COPY exemplos/ ./exemplos/

CMD ["python", "main.py"]
