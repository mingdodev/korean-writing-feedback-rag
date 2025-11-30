import os
import json
import csv
import time
from pathlib import Path
from kafka import KafkaConsumer

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "collect-events")
CSV_PATH = os.getenv("CSV_PATH", "/data/grammar_errors.csv")
CSV_FIELDS = [
    "user_id",
    "timestamp",
    "sentenceId",
    "originalText",
    "correctedText",
    "feedbacks"
]

def ensure_csv_header(path: Path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()

def main():
    csv_path = Path(CSV_PATH)
    ensure_csv_header(csv_path)

    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="error-data-collectors",
        enable_auto_commit=False,
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    print(f"[collector] Started. Reading from topic '{TOPIC}' ...")
    print(f"[collector] Writing CSV to {csv_path}")

    try:
        consumer.subscription()
        print(f"[collector] Successfully subscribed to topic {TOPIC}")
    except Exception as e:
        print(f"[collector] Subscription/Connection Error: {e}")

    while True:
        try:
            records_map = consumer.poll(timeout_ms=1000)
            if not records_map:
                print("[collector] INFO: Waiting for new records...")
                continue

            print(f"[collector] SUCCESS: Polled {sum(len(v) for v in records_map.values())} records. Starting CSV write...")

            with csv_path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)

                for messages in records_map.values():
                    for record in messages:
                        event = record.value
                        
                        feedback_data = event.get("feedbacks", [])
                        feedback_str = json.dumps(feedback_data, ensure_ascii=False)
                        
                        row = {
                            "user_id": event.get("userId", ""),
                            "timestamp": event.get("timestamp", ""),
                            "sentenceId": event.get("sentenceId", ""),
                            "originalText": event.get("originalText", ""),
                            "correctedText": event.get("correctedText", ""),
                            "feedbacks": feedback_str
                        }
                        writer.writerow(row)
            
            print("[collector] INFO: CSV write finished successfully.") 
            consumer.commit()

        except Exception as e:
            print(f"[collector] Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
