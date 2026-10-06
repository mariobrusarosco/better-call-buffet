from app.core.ai.client_new import AIClientNew
from uuid import UUID
from app.domains.talk_to_warren import router
from fastapi import APIRouter, Depends, Query
from app.core.dependencies import get_current_user_id

router = APIRouter()

router.post("/talk_to_warren", response_model=None)
def talk_to_warren_endpoint(
    message: str,
    user_id: UUID = Depends(get_current_user_id),
):
    ## Call the New AI client
    ai_client = AIClientNew()

        
    
    return "Hello I'm warren"
