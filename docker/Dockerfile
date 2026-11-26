FROM python:3.12.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY iniciar_web.py app_web.py main.py banco_dados.py modelos.py tipos.py cores.py migracao.py servico_risco.py avaliacao.py biblioteca.py catalogo_cvss.py relatorio.py ./
COPY interface_web/ ./interface_web/
COPY matematica/ ./matematica/
COPY exemplos/ ./exemplos/
COPY templates/ ./templates/
COPY static/ ./static/

RUN mkdir -p /dados && chown 65534:65534 /dados

EXPOSE 8000

CMD ["python", "main.py"]
