from fastapi import APIRouter, Depends
from ..schemas.feedback_request import FeedbackRequest
from ..schemas.feedback_response import FeedbackResponse
from ..services.feedback_facade import FeedbackFacade
from ..core.dependencies import get_feedback_facade
from ..util.security import get_session_id_from_request

router = APIRouter()

@router.post("/feedback", response_model=FeedbackResponse)
async def create_feedback(
    request: FeedbackRequest,
    facade: FeedbackFacade = Depends(get_feedback_facade),
    user_id: str = Depends(get_session_id_from_request)
):
    return await facade.create_feedback(request, user_id=user_id)
