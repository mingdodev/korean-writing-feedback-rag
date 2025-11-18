from pydantic import BaseModel

class FeedbackRequest(BaseModel):
    title: str
    contents: str
