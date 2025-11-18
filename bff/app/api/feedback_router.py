# app/api/feedback_router.py
from fastapi import APIRouter
from schemas.feedback_request import FeedbackRequest
from schemas.feedback_response import FeedbackResponse, ContextFeedback, Sentence, GrammarFeedback

router = APIRouter()

@router.post("/api/feedback", response_model=FeedbackResponse)
async def create_feedback(request: FeedbackRequest):

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

    context = ContextFeedback(
        feedback="This is a context feedback example."
    )

    sentences = [
        Sentence(
            sentence_id=1,
            original_sentence="This is a test sentence.",
            grammar_feedback=None
        )
    ]

    return FeedbackResponse(
        context_feedback=context,
        sentences=sentences
    )
