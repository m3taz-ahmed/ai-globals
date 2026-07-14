FROM python:3.11-slim

WORKDIR /app

COPY . .
RUN pip install -e '.[dev]'

EXPOSE 8080

CMD ["python", "dashboard/server.py"]
