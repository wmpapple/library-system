# app/routers/borrow.py
import logging
from datetime import datetime
from sqlalchemy.exc import NoResultFound

logger = logging.getLogger("uvicorn.error")
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from .. import models, schemas, crud
from ..dependencies import get_db_dependency, get_current_user, ensure_admin, get_token_payload
from ..security import TokenPayload

# ---------------------------------------------------------------------------
router = APIRouter(
    prefix="/borrow",
    tags=["Borrowing & Fines"] 
)

# ---------------------------------------------------------------------------
# Borrow records
# ---------------------------------------------------------------------------

@router.post("/", response_model=schemas.BorrowRecordRead)
async def borrow_book(
    request: schemas.BorrowBookRequest,
    db: Session = Depends(get_db_dependency),
    payload: TokenPayload = Depends(get_token_payload),
    current_user: models.User = Depends(get_current_user)
):
    record_data = schemas.BorrowRecordCreate(
        user_id=current_user.id,
        book_id=request.book_id,
        due_at=request.due_at
    )
    try:
        return crud.create_borrow_record(db, record_data, db_key=payload.db_key)
    except NoResultFound:
         raise HTTPException(status_code=404, detail="Book not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 获取我的借阅记录
@router.get("/me", response_model=List[schemas.BorrowRecordRead])
def read_my_borrows(
    db: Session = Depends(get_db_dependency),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieves all borrow records for the currently logged-in user."""
    return crud.get_borrow_records(db, user_id=current_user.id)


@router.get("/", response_model=List[schemas.BorrowRecordRead])
def list_borrow_records(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
):
    """
    Retrieves borrow records.
    - Admins can see all records.
    - Other users can only see their own.
    """
    user_id_filter = None
    if current_user.role != schemas.RoleEnum.ADMIN:
        user_id_filter = current_user.id
    return crud.get_borrow_records(db, user_id=user_id_filter)


@router.put("/{record_id}", response_model=schemas.BorrowRecordRead)
def update_borrow(
    record_id: int,
    payload: schemas.BorrowRecordUpdate,
    db: Session = Depends(get_db_dependency),
    token_payload: TokenPayload = Depends(get_token_payload),
    current_user: models.User = Depends(get_current_user),
):
    ensure_admin(current_user)
    try:
        return crud.update_borrow_record(db, record_id, payload, db_key=token_payload.db_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

@router.post("/return/{record_id}", response_model=schemas.BorrowRecordRead)
def return_book(
    record_id: int,
    db: Session = Depends(get_db_dependency),
    payload: TokenPayload = Depends(get_token_payload),
    current_user: models.User = Depends(get_current_user)
):
    try:
        return crud.return_book(db, record_id, current_user, db_key=payload.db_key)
    except NoResultFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record or book not found")
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{record_id}")
def delete_borrow(
    record_id: int,
    db: Session = Depends(get_db_dependency),
    payload: TokenPayload = Depends(get_token_payload),
    current_user: models.User = Depends(get_current_user),
):
    ensure_admin(current_user)
    try:
        crud.delete_borrow_record(db, record_id, db_key=payload.db_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"status": "deleted"}

# ---------------------------------------------------------------------------
# Fines
# ---------------------------------------------------------------------------

@router.post("/fines", response_model=schemas.FineRead)
def create_fine(
    payload: schemas.FineCreate,
    db: Session = Depends(get_db_dependency),
    token_payload: TokenPayload = Depends(get_token_payload),
    current_user: models.User = Depends(get_current_user),
):
    ensure_admin(current_user)
    return crud.create_fine(db, payload, db_key=token_payload.db_key)

@router.patch("/fines/{fine_id}", response_model=schemas.FineRead)
def mark_fine_paid(
    fine_id: int,
    payload: schemas.FineUpdate,
    db: Session = Depends(get_db_dependency),
    token_payload: TokenPayload = Depends(get_token_payload),
    current_user: models.User = Depends(get_current_user),
):
    # ensure_admin(current_user) # Removed this line, as all users can pay their own fines

    logger.debug(f"Attempting to mark fine {fine_id} paid by user {current_user.id} ({current_user.role})")
    try:
        # Retrieve the fine to check ownership
        db_fine = crud.get_fine_by_id(db, fine_id)
        if not db_fine:
            logger.debug(f"Fine {fine_id} not found.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fine not found")

        logger.debug(f"Fine {fine_id} found. Fine user_id: {db_fine.user_id}. Current user_id: {current_user.id}.")

        # Allow admin to update any fine, or user to update their own fine
        if current_user.role != schemas.RoleEnum.ADMIN and db_fine.user_id != current_user.id:
            logger.warning(f"User {current_user.id} (role: {current_user.role}) attempted to modify fine {fine_id} (owner: {db_fine.user_id}) without authorization.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this fine"
            )
        
        logger.info(f"User {current_user.id} authorized to update fine {fine_id}. Setting paid status to {payload.paid}.")
        return crud.update_fine(db, fine_id, paid=payload.paid, db_key=token_payload.db_key)
    except ValueError as exc:
        logger.error(f"Error updating fine {fine_id}: {exc}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
