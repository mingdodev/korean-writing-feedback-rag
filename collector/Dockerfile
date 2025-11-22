FROM python:3.14.0-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY consumer.py .

RUN mkdir -p /data

ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092
ENV KAFKA_TOPIC=collect-events
ENV CSV_PATH=/data/grammar_errors.csv

CMD ["python", "consumer.py"]