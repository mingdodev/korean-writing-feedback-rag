from typing import Optional
from pydantic import BaseModel

class ContextFeedback(BaseModel):
    feedback: str

class GrammarFeedback(BaseModel):
    corrected_sentence: str
    feedback: str

class Sentence(BaseModel):
    sentence_id: int
    original_sentence: str
    grammar_feedback: Optional[GrammarFeedback] = None

class FeedbackResponse(BaseModel):
    context_feedback: ContextFeedback
    sentences: list[Sentence]
    