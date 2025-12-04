import asyncio
import datetime
from typing import List

from .context_service import ContextService
from .grammar_service import GrammarService
from .sentence_service import SentenceService
from .collect_event_publisher import CollectEventPublisher, GrammarFeedbackEvent
from ..schemas.feedback_request import FeedbackRequest
from ..schemas.feedback_response import FeedbackResponse, ContextFeedback, GrammarFeedback, Sentence
from ..util.logger import log_task_exception, logger

class FeedbackFacade:
    def __init__(
        self,
        context_service: ContextService,
        grammar_service: GrammarService,
        sentence_service: SentenceService,
        collect_event_publisher: CollectEventPublisher,
    ):
        self.context_service = context_service
        self.grammar_service = grammar_service
        self.sentence_service = sentence_service
        self.collect_event_publisher = collect_event_publisher

    def _build_grammar_event(self, sentence: Sentence, user_id: str) -> GrammarFeedbackEvent:
        gf = sentence.grammar_feedback
        return GrammarFeedbackEvent(
            user_id=user_id,
            timestamp= datetime.datetime.now().isoformat(),
            sentence_id=sentence.sentence_id,
            original_text=sentence.original_sentence,
            corrected_text=gf.corrected_sentence,
            feedbacks=gf.feedbacks
        )

    async def create_feedback(self, request: FeedbackRequest, user_id: str) -> FeedbackResponse:
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
        logger.info(f"형태소 분석 기반 오류 후보 문장: {len(error_sentences)}개")

        for sentence in error_sentences:
            task = self.grammar_service.attach_grammar_feedback(sentence)
            grammar_tasks.append(task)

        # 5. 코루틴 동시 실행 및 응답 대기
        results = await asyncio.gather(
            context_task,
            *grammar_tasks,
            return_exceptions=True
        )

        # 6. 결과 분리
        context_result: ContextFeedback = results[0]
        grammar_feedbacks: list[GrammarFeedback | None] = results[1:]

        if isinstance(context_result, Exception):
            print(f"Context task failed: {context_result}")
            context_feedback = ContextFeedback(feedback="문맥 피드백 생성에 실패했습니다.") 
        else:
            context_feedback: ContextFeedback = context_result

        # 7. 생성한 문법 피드백을 원본 문장 데이터에 연결
        for sentence, result in zip(error_sentences, grammar_feedbacks):
            if isinstance(result, GrammarFeedback):
                sentence.grammar_feedback = result
            else:
                print(f"Grammar task for '{sentence.original_sentence}' failed: {result}")

        events: List[GrammarFeedbackEvent] = [
            self._build_grammar_event(sentence, user_id)
            for sentence in error_sentences
            if sentence.grammar_feedback is not None
        ]

        # 8. 별도의 스레드에서 새로운 데이터 수집 이벤트 발행
        if events:
            collector_task = asyncio.create_task(
                asyncio.to_thread(self.collect_event_publisher.publish_safe, events),
                name="Collect_Event_Publishing_Task"
            )
            collector_task.add_done_callback(log_task_exception)

        # 9. 최종 응답 데이터 정리 및 조립
        for sentence in sentences:
            # grammar_feedback이 있고, 그 안에 feedbacks 리스트가 비어있지 않으면 오류가 있는 문장
            if sentence.grammar_feedback and sentence.grammar_feedback.feedbacks:
                sentence.is_error = True
            else:
                sentence.is_error = False
                # is_error가 False이면 grammar_feedback을 null로 설정하여 불필요한 데이터 제외
                sentence.grammar_feedback = None

        return FeedbackResponse(
            context_feedback=context_feedback,
            sentences=sentences,
        )
