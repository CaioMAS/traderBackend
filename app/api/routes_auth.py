from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from app.core.security import verify_access_password, create_session_token, verify_session_token
from app.core.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    password: str

@router.post("/login")
async def login(req: LoginRequest):
    if not verify_access_password(req.password):
        raise HTTPException(status_code=401, detail="Senha de acesso incorreta.")
    
    token = create_session_token()
    return {
        "authenticated": True,
        "token": token,
        "message": "Acesso concedido à mesa de operações."
    }

@router.get("/status")
async def check_status(authorization: str | None = Header(None)):
    # Se nenhuma senha foi configurada no .env, acesso é sempre liberado
    if not settings.ACCESS_PASSWORD:
        return {"authenticated": True, "password_required": False}

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1]

    is_valid = verify_session_token(token)
    return {
        "authenticated": is_valid,
        "password_required": True
    }
