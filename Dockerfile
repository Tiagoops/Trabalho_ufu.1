FROM python:3.12.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# O inventário usa somente a biblioteca padrão do Python.
COPY main.py banco_dados.py modelos.py tipos.py cores.py ./

CMD ["python", "main.py"]
