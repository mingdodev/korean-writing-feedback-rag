from fastapi import APIRouter, Depends
from ..schemas.feedback_request import FeedbackRequest
from ..schemas.feedback_response import FeedbackResponse
from ..services.feedback_facade import FeedbackFacade
from ..core.dependencies import get_feedback_facade

router = APIRouter()

@router.post("/feedback", response_model=FeedbackResponse)
async def create_feedback(
    request: FeedbackRequest,
    facade: FeedbackFacade = Depends(get_feedback_facade),
):
    return await facade.create_feedback(request)
