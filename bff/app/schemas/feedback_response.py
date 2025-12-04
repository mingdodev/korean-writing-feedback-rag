from typing import List, Optional, Any
from pydantic import BaseModel, Field

"""문맥 피드백 관련 응답 모델"""

class ContextFeedback(BaseModel):
    feedback: str

""" 문법 피드백 관련 응답 모델"""

# ChromaDB 출력 모델
class ErrorWord(BaseModel):
    text: str = Field(..., description="오류 어절 -> 교정 어절 형태의 문자열")
    error_location: Optional[str] = Field(None, description="오류 위치")
    error_aspect: Optional[str] = Field(None, description="오류 양상")
    error_level: Optional[str] = Field(None, description="오류 층위")

class ErrorExample(BaseModel):
    original_sentence: str = Field(..., description="오류가 있는 원본 문장")
    error_words: List[ErrorWord] = Field(..., description="문장 내 오류 정보 목록")

# 1차 LLM 출력 모델
class CorrectionOutput(BaseModel):
    is_error: bool = Field(..., description="문장 오류 여부")
    corrected_sentence: str = Field(..., description="LLM이 교정한 문장")
    errors: List[str] = Field(..., description="교정된 문법 요소/형태 목록 (예: '과', '이')")

# 문법 정보 DB 출력 모델

class GrammarDBInfo(BaseModel):
    grammar_element: str
    explanation: str

# 2차 LLM 출력 모델

class FeedbackDetail(BaseModel):
    corrects: str = Field(..., description="틀린표현->맞은표현 형식의 교정 내용")
    reason: str = Field(..., description="해당 교정에 대한 설명/이유")

class GrammarFeedback(BaseModel):
    corrected_sentence: str
    feedbacks: List[FeedbackDetail]

"""최종 API 응답 모델"""

class Sentence(BaseModel):
    sentence_id: int
    original_sentence: str
    is_error: bool = False
    is_error_candidate: bool = Field(default=False, exclude=True)
    grammar_feedback: Optional[GrammarFeedback] = None

class FeedbackResponse(BaseModel):
    context_feedback: ContextFeedback
    sentences: list[Sentence]
    