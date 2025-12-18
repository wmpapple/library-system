# app/routers/seats.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..dependencies import get_db_dependency, get_current_user, ensure_admin, get_token_payload
from ..security import TokenPayload

router = APIRouter(
    prefix="/seats",
    tags=["Seats"]
)

# ---------------------------------------------------------------------------
# Seats and reservations
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[schemas.SeatRead])
def read_seats(db: Session = Depends(get_db_dependency)):
    return crud.list_seats(db)


@router.get("/stats", response_model=schemas.SeatStats)
def get_seat_stats(floor: int, db: Session = Depends(get_db_dependency)):
    """
    Get statistics for a specific floor, including the max seat number.
    """
    return crud.get_seat_stats_for_floor(db, floor=floor)


@router.post("/", response_model=schemas.SeatRead)
def add_seat(
    payload: schemas.SeatCreate,
    db: Session = Depends(get_db_dependency),
    token_payload: TokenPayload = Depends(get_token_payload),
    current_user: models.User = Depends(get_current_user),
):
    ensure_admin(current_user)
    return crud.create_seat(db, payload, db_key=token_payload.db_key)


@router.patch("/{seat_id}", response_model=schemas.SeatRead)
def set_seat_status(
    seat_id: int,
    status_value: str,
    db: Session = Depends(get_db_dependency),
    payload: TokenPayload = Depends(get_token_payload),
    current_user: models.User = Depends(get_current_user),
):
    ensure_admin(current_user)
    try:
        return crud.update_seat_status(db, seat_id, status_value, db_key=payload.db_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/reservations", response_model=schemas.SeatReservationRead)
def create_reservation(
    payload: schemas.SeatReservationCreate,
    db: Session = Depends(get_db_dependency),
    token_payload: TokenPayload = Depends(get_token_payload),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role == schemas.RoleEnum.STUDENT and payload.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot reserve for other users")
    
    # Check for existing active reservation using the new CRUD function
    if crud.get_user_active_reservation(db, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经有一个有效的预约，不能重复预约 (You already have an active reservation.)",
        )

    try:
        return crud.create_reservation(db, payload, db_key=token_payload.db_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc)
        ) from exc

@router.get("/reservations/me", response_model=Optional[schemas.SeatReservationRead], summary="获取我当前有效的预约")
def get_my_active_reservation(
    db: Session = Depends(get_db_dependency),
    current_user: models.User = Depends(get_current_user),
):
    """
    获取当前登录用户有效的座位预约。
    一个用户同时只能有一个状态为 'active' 的预约。
    """
    return crud.get_user_active_reservation(db, user_id=current_user.id)

@router.get("/reservations/history", response_model=List[schemas.SeatReservationRead], summary="获取我的所有座位预约记录 (包含历史)")
def get_my_all_reservations(
    db: Session = Depends(get_db_dependency),
    current_user: models.User = Depends(get_current_user),
):
    """
    获取当前登录用户所有的座位预约记录，包括已取消和已过期的。
    """
    return crud.get_user_all_reservations(db, current_user.id)

@router.post("/reservations/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    db: Session = Depends(get_db_dependency),
    payload: TokenPayload = Depends(get_token_payload),
    current_user: models.User = Depends(get_current_user),
):
    try:
        reservation = db.get(models.SeatReservation, reservation_id)
        if not reservation:
            raise ValueError("Reservation not found")
        if current_user.role == schemas.RoleEnum.STUDENT and reservation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Cannot cancel other users' reservations"
            )
        crud.cancel_reservation(db, reservation_id, db_key=payload.db_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"status": "cancelled"}