import json
from kafka import KafkaProducer

from .config import settings
from ..clients.context_llm_client import ContextLLMClient
from ..clients.grammar_llm_client import GrammarLLMClient
from ..llm.clova_client import ClovaStudioClient
from ..services.context_service import ContextService
from ..services.grammar_service import GrammarService
from ..services.sentence_service import SentenceService
from ..services.feedback_facade import FeedbackFacade
from ..services.collect_event_publisher import CollectEventPublisher

llm_client = ClovaStudioClient()

context_client = ContextLLMClient(llm_client)
grammar_client = GrammarLLMClient(llm_client)

context_service = ContextService(context_client)
grammar_service = GrammarService(grammar_client)
sentence_service = SentenceService()

kafka_producer = KafkaProducer(
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
)

collect_event_publisher = CollectEventPublisher(
    producer=kafka_producer,
    topic=settings.KAFKA_TOPIC,
    fallback_repo=None,
)

feedback_facade = FeedbackFacade(
    context_service=context_service,
    grammar_service=grammar_service,
    sentence_service=sentence_service,
    collect_event_publisher=collect_event_publisher,
)

def get_feedback_facade() -> FeedbackFacade:
    return feedback_facade
