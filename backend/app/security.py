"""Sécurité : hachage des mots de passe (bcrypt), jetons JWT et contrôle des rôles."""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import Role
from app.database import get_db
from app.models import User

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15

_bearer = HTTPBearer(auto_error=False)


# ------------------------------------------------------------------ mots de passe
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


# Hachage factice : même coût de calcul quand l'identifiant n'existe pas (évite de deviner les comptes)
DUMMY_HASH = hash_password("compte-inexistant")


def password_policy_error(password: str) -> str | None:
    """Politique du cahier des charges § 8.2. Renvoie un message d'erreur ou None."""
    if len(password) < 8:
        return "Le mot de passe doit contenir au moins 8 caractères."
    if len(password) > 72:
        return "Le mot de passe ne doit pas dépasser 72 caractères."
    if not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password):
        return "Le mot de passe doit contenir des majuscules et des minuscules."
    if not re.search(r"\d", password):
        return "Le mot de passe doit contenir au moins un chiffre."
    return None


# ------------------------------------------------------------------ jetons
def create_access_token(user: User, minutes: int) -> tuple[str, datetime]:
    s = get_settings()
    expires = datetime.now(UTC) + timedelta(minutes=minutes)
    payload = {"sub": str(user.id), "role": user.role, "exp": expires, "iat": datetime.now(UTC)}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm), expires


def _unauthorized(detail: str = "Session invalide ou expirée. Veuillez vous reconnecter.") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
                     db: Session = Depends(get_db)) -> User:
    if creds is None:
        raise _unauthorized("Authentification requise.")
    s = get_settings()
    try:
        payload = jwt.decode(creds.credentials, s.jwt_secret, algorithms=[s.jwt_algorithm])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _unauthorized() from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Compte inexistant ou désactivé.")
    return user


def require_roles(*roles: Role):
    """Dépendance FastAPI : refuse (403) si le rôle de l'utilisateur n'est pas dans la liste."""
    allowed = {r.value for r in roles}

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Votre rôle ne permet pas cette action.")
        return user

    return checker
