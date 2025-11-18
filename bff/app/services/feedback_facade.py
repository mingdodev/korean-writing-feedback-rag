from .context_service import ContextService
from .grammar_service import GrammarService
from .sentence_service import SentenceService
from ..schemas.feedback_request import FeedbackRequest
from ..schemas.feedback_response import FeedbackResponse, ContextFeedback, Sentence

class FeedbackFacade:
    def __init__(
        self,
        context_service: ContextService,
        grammar_service: GrammarService,
        sentence_service: SentenceService,
    ):
        self.context_service = context_service
        self.grammar_service = grammar_service
        self.sentence_service = sentence_service

    async def create_feedback(self, request: FeedbackRequest) -> FeedbackResponse:
        # 1. 문맥 피드백 서비스
        # request.title, request.contents로 LLM API 호출 -> context_feedback

        # 2. 문법 교정 서비스

        # requst.contents를 문장 단위로 분할 -> list[sentence]
        # sentencd: id, text

        # list[sentence] 각각에 대해 문장의 오류 포함 여부 판별 -> list[error_sentence]
        # error_sentence: id, text, grammar_feedback=None (아직)

        # list[error_sentence] 각각에 대해 문법 교정 서비스 호출 -> list[error_sentence]
        # error_sentence: id, text, grammar_feedback=LLMGrammarFeedback(...)
        # LLMGrammarFeedback: origin_sentence, corrected_sentence, feedback: str

        # list[sentence]를 순회하며 GrammarFeedback 매핑 -> list[sentence] (실제 API response)
        # 예) {sentence_id=1, original_sentence=..., grammar_feedback=None} 
        #   {sentence_id=2, original_sentence=..., grammar_feedback=GrammarFeedback(...)}
        # GrammarFeedback: corrected_sentence, feedback

        return FeedbackResponse(
            context_feedback=ContextFeedback(),
            sentences=[],
        )
