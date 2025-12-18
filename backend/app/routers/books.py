from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, crud, schemas
from ..dependencies import get_db_dependency, get_current_user, ensure_admin, get_token_payload
from ..security import TokenPayload

router = APIRouter(
    prefix="/books",
    tags=["Books"]
)

@router.get("/", response_model=List[schemas.BookRead])
def read_books(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db_dependency)
):
    return crud.list_books(db)

@router.post("/", response_model=schemas.BookBase)
def create_book(
    book: schemas.BookCreate,
    db: Session = Depends(get_db_dependency),
    payload: TokenPayload = Depends(get_token_payload),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="only the auth could add book !")
    try:
        return crud.create_book(db=db, book=book, db_key=payload.db_key)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="ISBN already registered.")


@router.put("/{book_id}", response_model=schemas.BookRead)
def update_book(
    book_id: int,
    book: schemas.BookBase,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
    payload: TokenPayload = Depends(get_token_payload),
):
    ensure_admin(current_user)
    try:
        return crud.update_book(db, book_id, book, db_key=payload.db_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

@router.delete("/{book_id}")
def remove_book(
    book_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
    payload: TokenPayload = Depends(get_token_payload),
):
    ensure_admin(current_user)
    try:
        crud.delete_book(db, book_id, db_key=payload.db_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"status": "deleted"}
