from ..schemas.feedback_response import Sentence, GrammarFeedback
from ..clients.grammar_llm_client import GrammarLLMClient

class GrammarService:
    def __init__(self, client: GrammarLLMClient):
        self.client = client
