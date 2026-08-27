FROM python:3.12-slim

# Sin .pyc y con logs sin buffer, para que salgan al instante en el contenedor.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

# Copiamos primero solo el manifiesto: si no cambian las dependencias, Docker
# reusa esta capa cacheada y no reinstala todo en cada build.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

# Usuario sin privilegios: si alguien se mete en el contenedor, no es root.
RUN useradd --create-home --uid 1001 fingrow
USER fingrow

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
