from fastapi import FastAPI
from .api.feedback_router import router as feedback_router

app = FastAPI()

app.include_router(feedback_router, prefix="/api")