FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

# Apply migrations before serving, every start - safe to run repeatedly (alembic no-ops if
# already at head). $PORT is set by the hosting platform (Render/Railway); 8000 is the local/
# docker-compose fallback.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
