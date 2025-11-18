from ..schemas.feedback_response import ContextFeedback
from ..clients.context_llm_client import ContextLLMClient

class ContextService:
    def __init__(self, client: ContextLLMClient):
        self.client = client

    async def create_context_feedback(self, title: str, contents: str) -> ContextFeedback:
        result = await self.client.get_context_feedback(title=title, contents=contents)

        return ContextFeedback(**result)
