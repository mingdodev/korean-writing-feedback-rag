from fastapi import FastAPI
from .schemas.feedback_request import FeedbackRequest
from .schemas.feedback_response import FeedbackResponse, ContextFeedback, Sentence
from .api.feedback_router import router as feedback_router

app = FastAPI()

app.include_router(feedback_router, prefix="/api")