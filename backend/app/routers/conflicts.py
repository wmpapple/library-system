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
