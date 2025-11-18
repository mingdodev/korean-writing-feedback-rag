from ..schemas.feedback_response import ContextFeedback
from ..clients.context_llm_client import ContextLLMClient

class ContextService:
    def __init__(self, client: ContextLLMClient):
        self.client = client

    async def create_context_feedback(self, title: str, contents: str) -> ContextFeedback:
        # LLM 호출 + 도메인 모델로 변환
        result = await self.client.request_context_feedback(title=title, contents=contents)
        return ContextFeedback(feedback=result.feedback_text)
