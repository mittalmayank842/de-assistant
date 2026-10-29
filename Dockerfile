FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
# CPU-only PyTorch: the default wheel bundles CUDA (~3 GB) that a CPU container never uses.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY docs ./docs
ENV PYTHONPATH=/app/src
ARG GIT_SHA=dev
ENV GIT_SHA=$GIT_SHA
EXPOSE 8000
CMD ["uvicorn", "de_assistant.api:app", "--host", "0.0.0.0", "--port", "8000"]
