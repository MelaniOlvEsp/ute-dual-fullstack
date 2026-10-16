FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace/ute-api-backend
COPY ute-api-backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY ute-api-backend/ ./
COPY database/schema_dual_desde_cero.sql /workspace/database/schema_dual_desde_cero.sql
COPY database/migrations/ /workspace/database/migrations/
RUN useradd --create-home appuser \
    && mkdir -p uploads/dual && chown -R appuser:appuser uploads
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
