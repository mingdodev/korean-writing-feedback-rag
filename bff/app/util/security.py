import uuid
from typing import Optional
from fastapi import Request, Response, Depends, HTTPException, status

def get_session_id_from_request(request: Request, response: Response) -> str:
    
    SESSION_COOKIE_NAME = "user_session_id"
    
    session_id = request.cookies.get(SESSION_COOKIE_NAME)

    if session_id:
        return session_id
    else:
        new_id = str(uuid.uuid4())
        
        response.set_cookie(
            key=SESSION_COOKIE_NAME, 
            value=new_id, 
            max_age=31536000 # 1년
        )
        return new_id