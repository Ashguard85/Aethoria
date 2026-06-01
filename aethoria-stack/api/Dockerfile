FROM python:3.12-slim
WORKDIR /app
# Context-Root ist aethoria-stack/ → Pfad muss api/ vorangestellt werden
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/main.py .
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
