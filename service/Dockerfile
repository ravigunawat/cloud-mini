FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 HF_HOME=/tmp/hf PIP_DEFAULT_TIMEOUT=120 PIP_RETRIES=10
RUN --mount=type=cache,target=/root/.cache/pip pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
COPY service/requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install -r /app/requirements.txt
COPY service/app.py service/validate.py /app/
COPY data/schema.json /app/schema.json
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
