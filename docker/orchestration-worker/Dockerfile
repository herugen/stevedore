ARG PREFECT_BASE_IMAGE=prefecthq/prefect:3.4-python3.12
FROM ${PREFECT_BASE_IMAGE}

ENV PREFECT_HOME=/opt/prefect
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY docker/orchestration-worker/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml ./
COPY stevedore ./stevedore

RUN pip install --no-cache-dir .

COPY docker/orchestration-worker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app

CMD ["/entrypoint.sh"]


