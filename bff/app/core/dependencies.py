from ..clients.context_llm_client import ContextLLMClient
from ..clients.grammar_llm_client import GrammarLLMClient
from ..services.context_service import ContextService
from ..services.grammar_service import GrammarService
from ..services.sentence_service import SentenceService
from ..services.feedback_facade import FeedbackFacade

context_client = ContextLLMClient()
grammar_client = GrammarLLMClient()

context_service = ContextService(context_client)
grammar_service = GrammarService(grammar_client)
sentence_service = SentenceService()

feedback_facade = FeedbackFacade(
    context_service=context_service,
    grammar_service=grammar_service,
    sentence_service=sentence_service,
)

def get_feedback_facade() -> FeedbackFacade:
    return feedback_facade
