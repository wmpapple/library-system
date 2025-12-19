from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..dependencies import get_db_dependency, ensure_admin, get_db_key_dependency
from ..database import get_session


router = APIRouter(
    prefix="/conflicts",
    tags=["conflicts"],
    dependencies=[Depends(ensure_admin)],
)

public_router = APIRouter(
    prefix="/conflicts",
    tags=["conflicts"],
)


@router.get("/", response_model=List[schemas.DataConflictRead])
def read_unresolved_conflicts(db: Session = Depends(get_db_dependency)):
    """
    Retrieve a list of unresolved data conflicts.
    """
    return crud.get_unresolved_conflicts(db)


@router.get("/{conflict_id}", response_model=schemas.DataConflictRead)
def read_conflict(conflict_id: int, db: Session = Depends(get_db_dependency)):
    """
    Retrieve a single data conflict by its ID.
    """
    db_conflict = crud.get_conflict_by_id(db, conflict_id=conflict_id)
    if db_conflict is None:
        raise HTTPException(status_code=404, detail="Conflict not found")
    return db_conflict


@router.post("/{conflict_id}/resolve", response_model=schemas.DataConflictRead)
def resolve_a_conflict(
    conflict_id: int,
    resolution: schemas.DataConflictUpdate,
    db_key: str = Depends(get_db_key_dependency),
):
    """
    Resolve a data conflict.
    """
    try:
        with get_session(resolution.source_db) as conflict_db_session:
            return crud.resolve_conflict(
                db=conflict_db_session,
                conflict_id=conflict_id,
                resolution=resolution,
                db_key=db_key,
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@public_router.post("/verify-access", response_model=schemas.DataConflictRead)
def verify_conflict_access(
    access_request: schemas.ConflictAccess
):
    """
    Verifies admin password against a token to grant access to conflict details.
    This is a public endpoint, but requires a short-lived token from an email.
    """
    from .. import security
    from ..database import SessionFactories, get_session

    try:
        payload = security.decode_conflict_view_token(access_request.token)
        admin_email = payload.get("sub")
        conflict_id = payload.get("conflict_id")
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Manually get a session from any available database engine
    # as user/conflict data should be synced.
    db_key = next(iter(SessionFactories.keys()))
    with get_session(db_key) as db:
        admin = crud.get_user_by_email(db, email=admin_email)
        if not admin:
            raise HTTPException(status_code=404, detail="Admin user not found")

        if not security.verify_password(access_request.password, admin.password_hash):
            raise HTTPException(status_code=401, detail="Incorrect password")

        db_conflict = crud.get_conflict_by_id(db, conflict_id=conflict_id)
        if db_conflict is None:
            raise HTTPException(status_code=404, detail="Conflict not found")

        return db_conflict
