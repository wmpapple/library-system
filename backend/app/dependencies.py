# app/dependencies.py
from typing import Iterator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .database import SessionFactories
from . import crud, models, schemas
from .security import decode_access_token, TokenPayload

# 定义认证方案
security = HTTPBearer()

def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenPayload:
    """Extracts and validates the payload from the JWT."""
    token = credentials.credentials
    try:
        return decode_access_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token"
        ) from exc


def get_db_dependency(
    payload: TokenPayload = Depends(get_token_payload)
) -> Iterator[Session]:
    """
    FastAPI dependency that yields a session based on the 'db_key' in the JWT.
    """
    db_key = payload.db_key
    if db_key not in SessionFactories:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Invalid database key '{db_key}' in token."
        )
    
    session = SessionFactories[db_key]()
    try:
        yield session
    finally:
        session.close()


def get_unprotected_db_dependency() -> Iterator[Session]:
    """
    FastAPI dependency that yields a session for unprotected endpoints.
    It defaults to the first configured database.
    """
    session = SessionFactories["MySQL"]()
    try:
        yield session
    finally:
        session.close()


def get_db_key_dependency(
    payload: TokenPayload = Depends(get_token_payload)
) -> str:
    """
    FastAPI dependency that extracts and returns the 'db_key' from the JWT.
    """
    return payload.db_key


def get_current_user(
    payload: TokenPayload = Depends(get_token_payload),
    db: Session = Depends(get_db_dependency),
) -> models.User:
    """
    Gets the current user from the database specified in the token.
    """
    username = payload.sub
    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User not found"
        )
    return user


def ensure_admin(user: models.User = Depends(get_current_user)) -> models.User:
    """
    确保当前用户是管理员。
    注意：这里可以直接依赖 get_current_user
    """
    if user.role != schemas.RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin privileges required"
        )
    return user