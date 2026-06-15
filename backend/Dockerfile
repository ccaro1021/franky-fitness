FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY models.py spoonacular.py exercisedb.py grocery.py ./
COPY backend/ ./backend/

CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT
