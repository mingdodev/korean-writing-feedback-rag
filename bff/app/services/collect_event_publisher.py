import logging
from kafka import KafkaProducer
from dataclasses import dataclass

@dataclass
class GrammarFeedbackEvent:
    sentence_id: int
    original_text: str
    corrected_text: str
    feedback: str

logger = logging.getLogger(__name__)


class CollectEventPublisher:
    def __init__(self, producer: KafkaProducer, topic: str, fallback_repo=None):
        self.producer = producer
        self.topic = topic
        self.fallback_repo = fallback_repo  # Optional: 실패 시 파일/DB에 저장

    def _to_record(self, event: "GrammarFeedbackEvent") -> dict:
        return {
            "sentenceId": event.sentence_id,
            "originalText": event.original_text,
            "correctedText": event.corrected_text,
            "feedback": event.feedback
        }

    def publish_safe(self, events: list["GrammarFeedbackEvent"]) -> None:

        if not events:
            return

        try:
            for event in events:
                record = self._to_record(event)
                self.producer.send(self.topic, value=record)
            self.producer.flush()
        except Exception as e:
            logger.error("Failed to publish grammar events to Kafka", exc_info=e)
            if self.fallback_repo:
                try:
                    self.fallback_repo.save(events)
                except Exception as e2:
                    logger.error("Failed to save grammar events to fallback store", exc_info=e2)
