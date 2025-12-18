from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas, models
from ..dependencies import get_current_user, get_db_dependency, ensure_admin, get_db_key_dependency

router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
)


@router.get("/", response_model=List[schemas.SystemSettingRead], summary="Get all system settings")
def read_settings(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency)
):
    ensure_admin(current_user)
    return crud.list_settings(db)


@router.put("/{key}", response_model=schemas.SystemSettingRead, summary="Update a system setting")
def update_setting(
    key: str,
    payload: schemas.SystemSettingUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
    db_key: str = Depends(get_db_key_dependency)
):
    ensure_admin(current_user)
    try:
        updated_setting = crud.set_setting(db, key=key, value=payload.value, db_key=db_key)
        return updated_setting
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
