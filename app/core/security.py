import hmac
import hashlib
import time
import secrets
from app.core.config import settings

# Gera uma chave secreta para assinatura dos tokens de sessão
SIGNING_KEY = settings.SECRET_KEY.encode("utf-8")

def verify_access_password(provided_password: str) -> bool:
    """Valida a senha fornecida contra a ACCESS_PASSWORD do .env."""
    expected = settings.ACCESS_PASSWORD
    if not expected:
        return True # Se não tiver senha configurada, permite acesso
    return hmac.compare_digest(provided_password.strip(), expected.strip())

def create_session_token() -> str:
    """Gera um token de sessão assinado com timestamp de validade (30 dias)."""
    # Formato: timestamp_epoch:random_hex:signature_hmac
    expires_at = int(time.time()) + (30 * 86400)
    nonce = secrets.token_hex(16)
    payload = f"{expires_at}:{nonce}"
    sig = hmac.new(SIGNING_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"

def verify_session_token(token: str | None) -> bool:
    """Valida se o token de sessão é legítimo e não expirou."""
    if not settings.ACCESS_PASSWORD:
        return True # Sem senha configurada = livre
    
    if not token:
        return False
    
    parts = token.strip().split(":")
    if len(parts) != 3:
        return False
    
    expires_str, nonce, sig = parts
    try:
        expires_at = int(expires_str)
        if time.time() > expires_at:
            return False # Expirado
    except ValueError:
        return False

    payload = f"{expires_at}:{nonce}"
    expected_sig = hmac.new(SIGNING_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected_sig)
