"""
Middleware e utilitários de Autenticação e Validação de IAP JWT.
"""
import time
import threading
import math
import requests
import jwt
from typing import Dict, Any, Optional, Iterable, Set
from fastapi import Request, HTTPException, status
from orchestrator.config import settings

# Cache das chaves públicas do IAP
_IAP_KEYS_CACHE: Dict[str, Any] = {}
_IAP_KEYS_LAST_FETCH = 0
_CACHE_TTL = 3600  # 1 hora
_KEY_REFRESH_INTERVAL = 60
_IAP_KEYS_LOCK = threading.Lock()


def _normalize_entries(entries: Iterable[str] | str, strip_at: bool = False) -> Set[str]:
    """Normaliza uma lista ou string CSV de domínios/e-mails para comparação estrita."""
    if isinstance(entries, str):
        items = entries.split(",")
    else:
        items = entries or []
    normalized: Set[str] = set()
    for item in items:
        val = str(item).strip().lower()
        if strip_at:
            val = val.lstrip("@")
        if val:
            normalized.add(val)
    return normalized


def get_iap_public_keys(force_refresh: bool = False) -> Dict[str, Any]:
    """Obtém as chaves públicas do Google IAP com cache em memória."""
    global _IAP_KEYS_CACHE, _IAP_KEYS_LAST_FETCH
    with _IAP_KEYS_LOCK:
        now = time.time()
        age = now - _IAP_KEYS_LAST_FETCH
        if _IAP_KEYS_CACHE and age < _CACHE_TTL and not (force_refresh and age >= _KEY_REFRESH_INTERVAL):
            return _IAP_KEYS_CACHE
        try:
            resp = requests.get("https://www.gstatic.com/iap/verify/public_key-jwk", timeout=10)
            resp.raise_for_status()
            keys = resp.json()
            if not isinstance(keys, dict) or not isinstance(keys.get("keys"), list) or not keys["keys"]:
                raise ValueError("Invalid IAP key set")
            for key in keys["keys"]:
                if (not isinstance(key, dict) or not isinstance(key.get("kid"), str)
                        or not key["kid"] or key.get("kty") != "EC" or key.get("crv") != "P-256"):
                    raise ValueError("Invalid IAP public key")
                jwt.algorithms.ECAlgorithm.from_jwk(key)
            _IAP_KEYS_CACHE = keys
            _IAP_KEYS_LAST_FETCH = now
            return _IAP_KEYS_CACHE
        except (requests.RequestException, ValueError, TypeError, KeyError, jwt.PyJWTError):
            # Never extend trust in expired keys after a failed refresh.
            raise HTTPException(status_code=503, detail="Chaves de autenticacao IAP indisponiveis.") from None


def validate_iap_jwt(jwt_token: str, expected_audience: Optional[str] = None) -> Dict[str, Any]:
    """
    Valida a assinatura ECDSA, emissor e claims do JWT emitido pelo Google IAP.
    """
    if not isinstance(expected_audience, str) or not expected_audience.strip():
        raise HTTPException(status_code=503, detail="Audiencia IAP nao configurada.")
    try:
        header = jwt.get_unverified_header(jwt_token)
        key_id = header.get("kid")
        if header.get("alg") != "ES256":
            raise HTTPException(status_code=401, detail="Algoritmo IAP invalido.")
        if not isinstance(key_id, str) or not key_id:
            raise HTTPException(status_code=401, detail="Token IAP inválido: 'kid' ausente no header.")

        jwks = get_iap_public_keys()
        key_dict = next((key for key in jwks["keys"] if key.get("kid") == key_id), None)
        if key_dict is None:
            # Refresh for rotated keys, but rate-limit unknown-kid requests.
            jwks = get_iap_public_keys(force_refresh=True)
            key_dict = next((key for key in jwks["keys"] if key.get("kid") == key_id), None)

        if not key_dict:
            raise HTTPException(status_code=401, detail="Token IAP inválido: Chave pública não encontrada.")

        try:
            public_key = jwt.algorithms.ECAlgorithm.from_jwk(key_dict)
        except (ValueError, TypeError, jwt.PyJWTError):
            raise HTTPException(status_code=503, detail="Chave de autenticacao IAP invalida.") from None

        options = {
            "verify_signature": True,
            "verify_aud": True,
            "verify_iss": True,
            "verify_exp": True,
            "require": ["exp", "iat", "aud", "iss", "sub", "email"],
            "strict_aud": True,
        }

        payload = jwt.decode(
            jwt_token,
            public_key,
            algorithms=["ES256"],
            audience=expected_audience,
            issuer="https://cloud.google.com/iap",
            options=options,
            leeway=30,
        )
        if (any(not isinstance(payload[field], str) or not payload[field] for field in ("sub", "email"))
                or any(isinstance(payload[field], bool) or not isinstance(payload[field], (int, float))
                       or not math.isfinite(payload[field])
                       for field in ("iat", "exp"))):
            raise jwt.InvalidTokenError("Invalid IAP claim types")
        if not 0 < payload["exp"] - payload["iat"] <= 660:
            raise jwt.InvalidTokenError("Invalid IAP token lifetime")
        return payload
    except (jwt.PyJWTError, ValueError, TypeError, OverflowError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Validação de IAP JWT falhou: {str(e)}"
        )


async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Dependência FastAPI que extrai o usuário autenticado.
    No modo 'iap', valida estritamente o header X-Goog-IAP-JWT-Assertion.
    No modo 'local', permite o usuário de desenvolvimento seguro.
    """
    if settings.AUTH_MODE == "local":
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Modo de autenticação local não permitido em ambiente de produção."
            )
        return {
            "sub": "local-dev-user-001",
            "email": settings.LOCAL_DEV_USER,
            "role": settings.LOCAL_DEV_ROLE,
            "auth_type": "local_dev"
        }

    iap_jwt = request.headers.get("X-Goog-IAP-JWT-Assertion")
    if not iap_jwt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso não autorizado: Cabeçalho 'X-Goog-IAP-JWT-Assertion' ausente."
        )

    claims = validate_iap_jwt(iap_jwt, settings.IAP_EXPECTED_AUDIENCE)

    # Extrai dados validados
    email = claims.get("email", "").strip().lower()
    sub = claims.get("sub", "")

    # Validação fail-closed de domínios autorizados (match estrito após '@')
    allowed_domains = _normalize_entries(settings.IAP_ALLOWED_DOMAINS, strip_at=True)
    if not allowed_domains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: nenhum domínio autorizado configurado."
        )

    if email.count("@") != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: identificador de e-mail inválido."
        )
    local_part, domain = email.split("@", 1)
    if not local_part or not domain or domain not in allowed_domains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a domínios corporativos autorizados."
        )

    # Determinação de Role por lista explícita de administradores
    admin_emails = _normalize_entries(settings.IAP_ADMIN_EMAILS)
    role = "admin" if email in admin_emails else "operator"

    return {
        "sub": sub,
        "email": email,
        "role": role,
        "auth_type": "google_iap",
        "claims": claims
    }
