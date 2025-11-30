import logging
from typing import List
from kafka import KafkaProducer
from dataclasses import dataclass

from ..schemas.feedback_response import FeedbackDetail

@dataclass
class GrammarFeedbackEvent:
    user_id: str
    timestamp: str
    sentence_id: int
    original_text: str
    corrected_text: str
    feedbacks: List[FeedbackDetail]

logger = logging.getLogger(__name__)

class CollectEventPublisher:
    def __init__(self, producer: KafkaProducer, topic: str, fallback_repo=None):
        self.producer = producer
        self.topic = topic
        self.fallback_repo = fallback_repo  # Optional: 실패 시 파일/DB에 저장

    def _to_record(self, event: "GrammarFeedbackEvent") -> dict:
        feedbacks_payload = []
        for fd in event.feedbacks:
            if hasattr(fd, "model_dump"):
                feedbacks_payload.append(fd.model_dump())
            elif hasattr(fd, "dict"):
                feedbacks_payload.append(fd.dict())
            else:
                feedbacks_payload.append(
                    {
                        "corrects": getattr(fd, "corrects", ""),
                        "reason": getattr(fd, "reason", ""),
                    }
                )

        return {
            "userId": event.user_id,
            "timestamp": event.timestamp,
            "sentenceId": event.sentence_id,
            "originalText": event.original_text,
            "correctedText": event.corrected_text,
            "feedbacks": feedbacks_payload,
        }

    def publish_safe(self, events: list["GrammarFeedbackEvent"]) -> None:

        if not events:
            logger.info("Attempted to publish, but event list is empty.")
            return

        try:
            logger.info(f"Attempting to publish {len(events)} grammar events to topic '{self.topic}'.")

            for event in events:
                record = self._to_record(event)
                self.producer.send(self.topic, value=record)

            self.producer.flush()
            logger.info(f"Successfully published {len(events)} events and flushed.")
            
        except Exception as e:
            logger.error("Failed to publish grammar events to Kafka", exc_info=e)
            if self.fallback_repo:
                try:
                    self.fallback_repo.save(events)
                except Exception as e2:
                    logger.error("Failed to save grammar events to fallback store", exc_info=e2)
