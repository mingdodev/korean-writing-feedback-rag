from .context_service import ContextService
from .grammar_service import GrammarService
from .sentence_service import SentenceService
from ..schemas.feedback_request import FeedbackRequest
from ..schemas.feedback_response import FeedbackResponse, ContextFeedback, GrammarFeedback, Sentence

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
        # 1. 문맥 피드백
        context_feedback: ContextFeedback = await self.context_service.create_context_feedback(
            title=request.title,
            contents=request.contents,
        )

        # 2. 문장 분할
        sentences = self.sentence_service.split_into_sentences(request.contents)

        # 3. 오류를 포함한 문장 태깅
        sentences = self.sentence_service.tag_error_sentences_by_konlpy(sentences)

        # 4. 문법 교정: 오류 문장만 LLM 호출
        
        for sentence in sentences:
            if not sentence.is_error_candidate:
                continue

            feedback: GrammarFeedback = await self.grammar_service.attach_grammar_feedback([sentence])
            if feedback:
                sentence.grammar_feedback = feedback


        # 5. 최종 응답 조립
        return FeedbackResponse(
            context_feedback=context_feedback,
            sentences=sentences,
        )
