FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace/ute-api-clean
COPY ute-api-clean/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY ute-api-clean/ ./
COPY database/schema_dual_desde_cero.sql /workspace/database/schema_dual_desde_cero.sql
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
