"""Module 1 – Authentification : connexion, renouvellement de session, profil."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginIn, PasswordChange, ProfileUpdate, TokenOut, UserOut
from app.security import (DUMMY_HASH, LOCK_MINUTES, MAX_FAILED_ATTEMPTS, create_access_token, get_current_user,
                          hash_password, password_policy_error, verify_password)
from app.services.common import audit, get_int_setting

router = APIRouter(prefix="/auth", tags=["Authentification"])


def _token(db: Session, user: User) -> TokenOut:
    token, exp = create_access_token(user, get_int_setting(db, "session_minutes"))
    return TokenOut(access_token=token, expires_at=exp, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))
    maintenant = datetime.now(UTC)
    if user is None:
        verify_password(data.password, DUMMY_HASH)  # même durée de traitement qu'un compte existant
        audit(db, None, "CONNEXION_ECHEC", "user", None, "identifiant inconnu", request, username=data.username[:30])
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiant ou mot de passe incorrect.")
    if user.locked_until and user.locked_until > maintenant:
        minutes = int((user.locked_until - maintenant).total_seconds() // 60) + 1
        raise HTTPException(status.HTTP_423_LOCKED,
                            f"Compte temporairement bloqué après {MAX_FAILED_ATTEMPTS} échecs. "
                            f"Réessayez dans {minutes} minute(s).")
    if not verify_password(data.password, user.password_hash):
        user.failed_attempts += 1
        detail = f"tentative {user.failed_attempts}"
        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until, user.failed_attempts = maintenant + timedelta(minutes=LOCK_MINUTES), 0
            detail += f" – compte bloqué {LOCK_MINUTES} min"
        audit(db, user, "CONNEXION_ECHEC", "user", user.id, detail, request)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiant ou mot de passe incorrect.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce compte est désactivé. Contactez l'administrateur.")
    user.failed_attempts, user.locked_until, user.last_login_at = 0, None, maintenant
    audit(db, user, "CONNEXION", "user", user.id, None, request)
    db.commit()
    return _token(db, user)


@router.post("/refresh", response_model=TokenOut)
def refresh(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Renouvelle la session tant que l'utilisateur est actif (jeton encore valide)."""
    return _token(db, user)


@router.post("/logout", status_code=204)
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audit(db, user, "DECONNEXION", "user", user.id, None, request)
    db.commit()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserOut)
def update_me(data: ProfileUpdate, request: Request, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    user.full_name, user.email = data.full_name, data.email
    audit(db, user, "MAJ_PROFIL", "user", user.id, None, request)
    db.commit()
    return user


@router.post("/change-password", status_code=204)
def change_password(data: PasswordChange, request: Request, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(422, "Le mot de passe actuel est incorrect.")
    if data.new_password == data.current_password:
        raise HTTPException(422, "Le nouveau mot de passe doit être différent de l'actuel.")
    if err := password_policy_error(data.new_password):
        raise HTTPException(422, err)
    user.password_hash = hash_password(data.new_password)
    audit(db, user, "CHANGEMENT_MDP", "user", user.id, None, request)
    db.commit()
