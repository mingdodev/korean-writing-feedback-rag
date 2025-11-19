import asyncio
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
        # 1. 문맥 피드백 코루틴 준비
        context_task = self.context_service.create_context_feedback(
            title=request.title,
            contents=request.contents,
        )

        # 2. 문장 분할
        sentences = self.sentence_service.split_into_sentences(request.contents)

        # 3. 오류를 포함한 문장 태깅
        sentences = self.sentence_service.tag_error_sentences_by_konlpy(sentences)

        # 4. 문법 교정 코루틴 리스트 준비
        grammar_tasks = []
        error_sentences = [s for s in sentences if s.is_error_candidate]

        for sentence in error_sentences:
            task = self.grammar_service.attach_grammar_feedback(sentence)
            grammar_tasks.append(task)

        # 5. 코루틴 동시 실행 및 응답 대기
        results = await asyncio.gather(context_task, *grammar_tasks)

        # 6. 결과 분리
        context_feedback: ContextFeedback = results[0]
        grammar_feedbacks: list[GrammarFeedback | None] = results[1:]

        # 7. 생성한 문법 피드백을 원본 문장 데이터에 연결
        for sentence, feedback in zip(error_sentences, grammar_feedbacks):
            if feedback:
                sentence.grammar_feedback = feedback

        # 8. 최종 응답 조립
        return FeedbackResponse(
            context_feedback=context_feedback,
            sentences=sentences,
        )
