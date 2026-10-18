# Backend WineGuard (FastAPI). Contexto de build: a pasta backend/.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências primeiro (aproveita o cache quando só o código muda)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

# A configuração vem de variáveis de ambiente (env_file no compose); o .env não entra na imagem.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
