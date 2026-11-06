FROM python:3.11-slim
RUN pip install --no-cache-dir boto3==1.35.36
WORKDIR /app
COPY worker/worker.py /app/worker.py
COPY prompts/teacher_prompt.txt /app/prompts/teacher_prompt.txt
CMD ["python", "-u", "/app/worker.py"]
