FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py keymaster.py ./

EXPOSE 8788

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8788"]
