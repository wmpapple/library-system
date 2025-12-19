"""CRUD helpers that also trigger multi-database synchronisation."""
from __future__ import annotations

import logging
import math # New import
from datetime import datetime, timedelta, date
from typing import Iterable, List, Optional
from collections import defaultdict

import sqlalchemy
from sqlalchemy import func, select, case
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session, joinedload

from . import models, schemas
from .database import get_session, SessionFactories
from .security import hash_password, verify_password
from .sync_manager import SyncManager
from .consistency import pre_modification_check
from .config import (
    OVERDUE_BORROW_GRACE_PERIOD_KEY,
    DEFAULT_OVERDUE_BORROW_GRACE_PERIOD,
    FINE_PER_UNIT, # New import
    FINE_UNIT_MINUTES # New import
)

logger = logging.getLogger("uvicorn.error")



# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.execute(select(models.User).where(models.User.username == username)).scalar_one_or_none()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.execute(select(models.User).where(models.User.email == email)).scalar_one_or_none()


def get_admin_users(db: Session) -> List[models.User]:
    """Retrieves a list of all admin users."""
    return list(db.execute(select(models.User).where(models.User.role == "admin")).scalars())




def create_user(db: Session, user: schemas.UserCreate, db_key: str) -> models.User:
    db_user = models.User(
        username=user.username,
        password_hash=hash_password(user.password),
        role=user.role,
        email=user.email,
    )
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Username already exists") from exc
    db.refresh(db_user)
    manager = SyncManager(source_db=db_key)
    manager.sync_instance(db_user)
    return db_user


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    user = get_user_by_username(db, username)
    if user and verify_password(password, user.password_hash):
        return user
    return None


# ---------------------------------------------------------------------------
# Book management
# ---------------------------------------------------------------------------

def list_books(db: Session) -> List[models.Book]:
    return list(db.execute(select(models.Book)).scalars())


def create_book(db: Session, book: schemas.BookCreate, db_key: str) -> models.Book:
    db_book = models.Book(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    manager = SyncManager(source_db=db_key)
    manager.sync_instance(db_book)
    return db_book


def update_book(db: Session, book_id: int, payload: schemas.BookBase, db_key: str) -> models.Book:
    pre_modification_check(models.Book, book_id, db_key)
    db_book = db.get(models.Book, book_id)
    if not db_book:
        raise ValueError("Book not found")

    borrowed_count = db.scalar(
        select(func.count(models.BorrowRecord.id)).where(
            models.BorrowRecord.book_id == book_id,
            models.BorrowRecord.returned_at == None
        )
    ) or 0

    if payload.total_copies < borrowed_count:
        raise ValueError(f"Book count cannot be less than borrowed count ({borrowed_count})")

    for key, value in payload.dict().items():
        setattr(db_book, key, value)

    # Recalculate available_copies to ensure consistency
    db_book.available_copies = db_book.total_copies - borrowed_count

    db.commit()
    db.refresh(db_book)
    manager = SyncManager(source_db=db_key)
    manager.sync_instance(db_book)
    return db_book


def delete_book(db: Session, book_id: int, db_key: str) -> None:
    pre_modification_check(models.Book, book_id, db_key)
    db_book = db.get(models.Book, book_id)
    if not db_book:
        raise ValueError("Book not found")

    borrowed_count = db.scalar(
        select(func.count(models.BorrowRecord.id)).where(
            models.BorrowRecord.book_id == book_id,
            models.BorrowRecord.returned_at == None
        )
    ) or 0

    if borrowed_count > 0:
        raise ValueError(f"Cannot delete book with active borrows ({borrowed_count})")

    db.delete(db_book)
    db.commit()
    manager = SyncManager(source_db=db_key)
    manager.delete_instance(models.Book, book_id)


# ---------------------------------------------------------------------------
# Borrow records
# ---------------------------------------------------------------------------

def create_borrow_record(db: Session, payload: schemas.BorrowRecordCreate, db_key: str) -> models.BorrowRecord:
    # Get and lock the book row
    book = db.query(models.Book).filter(models.Book.id == payload.book_id).with_for_update().one()

    if book.available_copies < 1:
        raise ValueError("No copies available")

    # Decrement stock
    book.available_copies -= 1

    # Create borrow record
    db_record = models.BorrowRecord(**payload.dict(), status="borrowed")
    db.add(db_record)
    
    # Commit transaction
    db.commit()

    # Refresh instances
    db.refresh(db_record)
    db.refresh(book)

    # Sync both instances
    manager = SyncManager(source_db=db_key)
    manager.sync_instance(db_record)
    manager.sync_instance(book)

    return db_record

def return_book(db: Session, record_id: int, user: models.User, db_key: str) -> models.BorrowRecord:
    # Get and lock the record
    db_record = db.query(models.BorrowRecord).filter(models.BorrowRecord.id == record_id).with_for_update().one()

    # If a regular user, can only return their own book
    if user.role != "admin" and db_record.user_id != user.id:
        raise PermissionError("User does not have permission for this record")

    if db_record.returned_at:
        raise ValueError("Book has already been returned")

    # Get and lock the book
    book = db.query(models.Book).filter(models.Book.id == db_record.book_id).with_for_update().one()

    # --- Pre-modification Consistency Checks ---
    pre_modification_check(models.BorrowRecord, record_id, db_key)
    pre_modification_check(models.Book, book.id, db_key)
    # --- End Checks ---

    # Update record and stock
    db_record.returned_at = datetime.utcnow()
    db_record.status = "returned"
    book.available_copies += 1

    # --- Fine Calculation and Creation/Update ---
    fine_to_sync: Optional[models.Fine] = None
    if db_record.returned_at > db_record.due_at:
        fine_amount = _calculate_fine_amount(db_record, db_record.returned_at)
        if fine_amount > 0:
            # Check for existing unpaid fine for this borrow record
            existing_fine = db.query(models.Fine).filter(
                models.Fine.borrow_record_id == db_record.id,
                models.Fine.paid == False
            ).one_or_none()

            if existing_fine:
                pre_modification_check(models.Fine, existing_fine.id, db_key)
                existing_fine.amount = fine_amount
                existing_fine.calculated_at = datetime.utcnow()
                db.add(existing_fine) # Mark as dirty for update
                logger.info(f"Updated fine for borrow record {db_record.id} to {fine_amount}.")
                fine_to_sync = existing_fine
            else:
                # Create a new fine record
                new_fine = models.Fine(
                    user_id=db_record.user_id,
                    borrow_record_id=db_record.id,
                    amount=fine_amount,
                    calculated_at=datetime.utcnow(),
                    paid=False
                )
                db.add(new_fine)
                logger.info(f"Created new fine of {fine_amount} for borrow record {db_record.id}.")
                fine_to_sync = new_fine
        else:
            logger.info(f"Book returned late but fine amount is 0 for borrow record {db_record.id}.")
    else:
        logger.info(f"Book returned on time for borrow record {db_record.id}.")
    # --- End Fine Logic ---

    db.commit()

    # Refresh all modified instances
    db.refresh(db_record)
    db.refresh(book)
    if fine_to_sync:
        db.refresh(fine_to_sync)

    # Sync all modified instances
    manager = SyncManager(source_db=db_key)
    manager.sync_instance(db_record)
    manager.sync_instance(book)
    if fine_to_sync:
        manager.sync_instance(fine_to_sync)

    return db_record


def update_borrow_record(
    db: Session, record_id: int, payload: schemas.BorrowRecordUpdate, db_key: str
) -> models.BorrowRecord:
    pre_modification_check(models.BorrowRecord, record_id, db_key)
    db_record = db.get(models.BorrowRecord, record_id)
    if not db_record:
        raise ValueError("Borrow record not found")
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(db_record, key, value)
    db.commit()
    db.refresh(db_record)
    manager = SyncManager(source_db=db_key)
    manager.sync_instance(db_record)
    return db_record


def delete_borrow_record(db: Session, record_id: int, db_key: str) -> None:
    pre_modification_check(models.BorrowRecord, record_id, db_key)
    db_record = db.get(models.BorrowRecord, record_id)
    if not db_record:
        raise ValueError("Borrow record not found")
    db.delete(db_record)
    db.commit()
    manager = SyncManager(source_db=db_key)
    manager.delete_instance(models.BorrowRecord, record_id)


def get_borrow_records(db: Session, user_id: Optional[int] = None) -> List[models.BorrowRecord]:
    """
    Retrieves borrow records.
    If user_id is provided, retrieves records for that user.
    Otherwise, retrieves all borrow records.
    Includes fine information for each record.
    """
    query = select(models.BorrowRecord).options(joinedload(models.BorrowRecord.fine))
    if user_id:
        query = query.where(models.BorrowRecord.user_id == user_id)
    return list(db.execute(query).scalars())


# ---------------------------------------------------------------------------
# Fine calculation helper
# ---------------------------------------------------------------------------

def _calculate_fine_amount(
    borrow_record: models.BorrowRecord,
    calculation_time: datetime # Use calculation_time, not current_time, for clarity
) -> float:
    logger.debug(f"[_calculate_fine_amount] Processing borrow record {borrow_record.id}. Due at: {borrow_record.due_at}, Calculation time: {calculation_time}")

    if calculation_time <= borrow_record.due_at:
        logger.debug(f"[_calculate_fine_amount] Calculation time ({calculation_time}) is not after due_at ({borrow_record.due_at}). Returning 0.0 fine.")
        return 0.0

    overdue_duration = calculation_time - borrow_record.due_at
    overdue_seconds = overdue_duration.total_seconds()
    overdue_minutes = overdue_seconds / 60
    logger.debug(f"[_calculate_fine_amount] Overdue duration: {overdue_duration}, Overdue seconds: {overdue_seconds}, Overdue minutes: {overdue_minutes}")

    if overdue_minutes <= 0: # This condition should now rarely be met if calculation_time > borrow_record.due_at
        logger.debug(f"[_calculate_fine_amount] Overdue minutes is <= 0 ({overdue_minutes}). Returning 0.0 fine.")
        return 0.0

    # Calculate fine based on units of 5 minutes, rounding up to the nearest unit
    fine_units = math.ceil(overdue_minutes / FINE_UNIT_MINUTES)
    fine_amount = fine_units * FINE_PER_UNIT
    logger.debug(f"[_calculate_fine_amount] Fine units: {fine_units}, Fine amount: {fine_amount}")

    return round(fine_amount, 2) # Round to 2 decimal places for currency


# ---------------------------------------------------------------------------
# Fines
# ---------------------------------------------------------------------------

def create_fine(db: Session, payload: schemas.FineCreate, db_key: str) -> models.Fine:
    db_fine = models.Fine(**payload.dict())
    db.add(db_fine)
    db.commit()
    db.refresh(db_fine)
    manager = SyncManager(source_db=db_key)
    manager.sync_instance(db_fine)
    return db_fine


def update_fine(db: Session, fine_id: int, *, paid: bool, db_key: str) -> models.Fine:
    pre_modification_check(models.Fine, fine_id, db_key)
    db_fine = db.get(models.Fine, fine_id)
    if not db_fine:
        raise ValueError("Fine not found")
    db_fine.paid = paid
    db.commit()
    db.refresh(db_fine)
    manager = SyncManager(source_db=db_key)
    manager.sync_instance(db_fine)
    return db_fine

def get_fine_by_id(db: Session, fine_id: int) -> Optional[models.Fine]:
    """Retrieves a fine by its ID."""
    return db.get(models.Fine, fine_id)


# ---------------------------------------------------------------------------
# Seats and reservations
# ---------------------------------------------------------------------------

def create_seat(db: Session, payload: schemas.SeatCreate, db_key: str) -> models.Seat:
    db_seat = models.Seat(**payload.dict())
    db.add(db_seat)
    db.commit()
    db.refresh(db_seat)
    manager = SyncManager(source_db=db_key)
    manager.sync_instance(db_seat)
    return db_seat


def list_seats(db: Session) -> List[models.Seat]:
    seats = db.execute(select(models.Seat)).scalars().all()
    current_time = datetime.utcnow()

    # Fetch all active reservation seat IDs in one query.
    active_reservation_seat_ids = {
        r.seat_id for r in db.query(models.SeatReservation.seat_id).filter(
            models.SeatReservation.status == "active",
            models.SeatReservation.expires_at > current_time
        ).all()
    }

    # Update seat status in memory without N+1 queries.
    for seat in seats:
        if seat.id in active_reservation_seat_ids:
            seat.status = "occupied"  # Dynamically update status for frontend display
        else:
            seat.status = "available"  # Ensure it's available if no active reservation
    return seats




def update_seat_status(db: Session, seat_id: int, status: str, db_key: str) -> models.Seat:
    pre_modification_check(models.Seat, seat_id, db_key)
    db_seat = db.get(models.Seat, seat_id)
    if not db_seat:
        raise ValueError("Seat not found")
    db_seat.status = status
    db.commit()
    db.refresh(db_seat)
    manager = SyncManager(source_db=db_key)
    manager.sync_instance(db_seat)
    return db_seat


def create_reservation(db: Session, payload: schemas.SeatReservationCreate, db_key: str) -> models.SeatReservation:
    # Acquire a pessimistic lock on the Seat object to prevent race conditions
    seat = db.query(models.Seat).filter(models.Seat.id == payload.seat_id).with_for_update().one_or_none()

    if not seat:
        raise ValueError("Seat not found")

    # --- Pre-modification Consistency Check for the Seat ---
    pre_modification_check(models.Seat, payload.seat_id, db_key)
    # --- End Check ---

    # Check for any existing active SeatReservation for the specific seat_id
    # that overlaps with the requested time frame.
    # Overlap condition: (start1 < end2) and (end1 > start2)
    # where start1, end1 are existing reservation times and start2, end2 are new reservation times.
    overlapping_reservation = db.query(models.SeatReservation).filter(
        models.SeatReservation.seat_id == payload.seat_id,
        models.SeatReservation.status == "active",
        models.SeatReservation.expires_at > datetime.utcnow(),
        models.SeatReservation.reserved_at < datetime.utcnow()
    ).first()

    if overlapping_reservation:
        raise ValueError("Seat is already reserved for the requested time frame.")
    
    # Also check the current status of the seat
    if seat.status != "available":
        raise ValueError(f"Seat is currently {seat.status} and cannot be reserved.")

    # Create the reservation
    db_reservation = models.SeatReservation(**payload.dict())
    db.add(db_reservation)

    # Update the seat status to 'occupied'
    seat.status = "occupied"

    db.commit()
    db.refresh(db_reservation)
    db.refresh(seat) # Refresh seat to reflect status change

    manager = SyncManager(source_db=db_key)
    manager.sync_instance(db_reservation)
    manager.sync_instance(seat) # Sync the updated seat as well
    return db_reservation


def cancel_reservation(db: Session, reservation_id: int, db_key: str) -> None:
    # Acquire a pessimistic lock on the reservation and the associated seat
    db_reservation = db.query(models.SeatReservation).filter(models.SeatReservation.id == reservation_id).with_for_update().one_or_none()

    if not db_reservation:
        raise ValueError("Reservation not found")
    
    # Ensure the reservation is active before cancelling
    if db_reservation.status != "active":
        raise ValueError("Reservation is not active and cannot be cancelled.")

    seat = db.query(models.Seat).filter(models.Seat.id == db_reservation.seat_id).with_for_update().one_or_none()
    
    # --- Pre-modification Consistency Checks ---
    pre_modification_check(models.SeatReservation, reservation_id, db_key)
    if seat:
        pre_modification_check(models.Seat, seat.id, db_key)
    # --- End Checks ---
    
    if not seat:
        # This case should ideally not happen if data integrity is maintained
        logger.warning(f"Seat with ID {db_reservation.seat_id} not found for reservation {reservation_id}")

    db_reservation.status = "cancelled"
    db_reservation.cancelled_at = datetime.utcnow()
    # If the seat exists, update its status back to 'available'
    if seat:
        seat.status = "available"

    db.commit()
    db.refresh(db_reservation)
    if seat: # Refresh seat only if it was found
        db.refresh(seat)

    manager = SyncManager(source_db=db_key)
    manager.sync_instance(db_reservation)
    if seat: # Sync seat only if it was found
        manager.sync_instance(seat)


def get_seat_stats_for_floor(db: Session, floor: int) -> schemas.SeatStats:
    """
    Get statistics for a specific floor, including the max seat number.
    """
    seats_on_floor = db.query(models.Seat).filter(models.Seat.floor == floor).all()
    
    max_num = 0
    if seats_on_floor:
        seat_numbers = []
        for seat in seats_on_floor:
            try:
                # Assuming code format is like 'F1-001', 'A2-023'
                num_part = seat.code.split('-')[-1]
                seat_numbers.append(int(num_part))
            except (ValueError, IndexError):
                continue # Skip codes that don't match the format
        
        if seat_numbers:
            max_num = max(seat_numbers)
            
    return schemas.SeatStats(
        total_count=len(seats_on_floor),
        max_seat_num=max_num
    )


def get_user_active_reservation(db: Session, user_id: int) -> Optional[models.SeatReservation]:
    """
    Retrieves the active seat reservation for a given user.
    A user can only have one 'active' reservation at a time.
    """
    return db.query(models.SeatReservation).filter(
        models.SeatReservation.user_id == user_id,
        models.SeatReservation.status == "active"
    ).first()


def default_overdue_reservations(db: Session, db_key: str) -> int:
    """
    Checks for overdue active seat reservations and defaults them.
    Returns the number of reservations defaulted.
    """
    current_time = datetime.utcnow()
    
    # Find active reservations that have expired
    overdue_reservations = db.query(models.SeatReservation).filter(
        models.SeatReservation.status == "active",
        models.SeatReservation.expires_at < current_time
    ).with_for_update(nowait=True).all() # Use nowait to avoid blocking if already locked
    
    defaulted_count = 0
    for db_reservation in overdue_reservations:
        try:
            # Update reservation status and cancelled_at
            db_reservation.status = "expired"
            db_reservation.cancelled_at = current_time # Set cancellation time as now
            
            # Update associated seat status
            seat = db.query(models.Seat).filter(models.Seat.id == db_reservation.seat_id).one_or_none()
            if seat:
                seat.status = "available"
            
            db.commit()
            db.refresh(db_reservation)
            if seat:
                db.refresh(seat)
            
            manager = SyncManager(source_db=db_key)
            manager.sync_instance(db_reservation)
            if seat:
                manager.sync_instance(seat)
            
            defaulted_count += 1
        except Exception as e:
            db.rollback()
            logger.error(f"Error defaulting reservation {db_reservation.id}: {e}")
            
    return defaulted_count


def default_overdue_borrow_records(db: Session, db_key: str) -> int:
    """
    Checks for overdue borrow records (not yet returned, past due date) and updates their status to "overdue".
    Returns the number of records updated.
    """
    current_time = datetime.utcnow()

    # Get grace period from system settings
    grace_period_seconds = DEFAULT_OVERDUE_BORROW_GRACE_PERIOD
    setting = get_setting(db, OVERDUE_BORROW_GRACE_PERIOD_KEY)
    if setting and setting.value.isdigit():
        grace_period_seconds = max(0, int(setting.value)) # Ensure grace period is non-negative

    # Calculate the exact time a book becomes overdue, considering the grace period
    # A book is overdue if its due_at is before (current_time - grace_period_seconds)
    overdue_threshold = current_time - timedelta(seconds=grace_period_seconds)

    # Find borrowed books that are past their due_at (adjusted by grace period) and not yet returned
    overdue_borrows = db.query(models.BorrowRecord).filter(
        models.BorrowRecord.status.in_(["borrowed", "overdue"]), # Check for both statuses
        models.BorrowRecord.due_at < overdue_threshold, # Apply grace period here
        models.BorrowRecord.returned_at == None
    ).with_for_update(nowait=True).all() # Use nowait to avoid blocking if already locked

    updated_count = 0
    for db_borrow_record in overdue_borrows:
        try:
            # --- Check for Status Change ---
            status_changed = db_borrow_record.status != "overdue"
            if status_changed:
                db_borrow_record.status = "overdue"

            # --- Fine Calculation and Creation/Update for currently overdue books ---
            fine_amount = _calculate_fine_amount(db_borrow_record, current_time)
            fine_instance_to_sync = None
            fine_changed = False

            if fine_amount > 0:
                existing_fine = db.query(models.Fine).filter(
                    models.Fine.borrow_record_id == db_borrow_record.id,
                    models.Fine.paid == False
                ).one_or_none()

                if existing_fine:
                    # Only update if amount has changed to the nearest cent
                    if not math.isclose(existing_fine.amount, fine_amount, rel_tol=1e-9, abs_tol=0.01):
                        existing_fine.amount = fine_amount
                        existing_fine.calculated_at = datetime.utcnow()
                        db.add(existing_fine)
                        fine_instance_to_sync = existing_fine
                        fine_changed = True
                        logger.info(f"Updated fine for currently overdue borrow record {db_borrow_record.id} to {fine_amount:.2f}.")
                else:
                    db_fine = models.Fine(
                        user_id=db_borrow_record.user_id,
                        borrow_record_id=db_borrow_record.id,
                        amount=fine_amount,
                        calculated_at=datetime.utcnow(),
                        paid=False
                    )
                    db.add(db_fine)
                    fine_instance_to_sync = db_fine
                    fine_changed = True
                    logger.info(f"Created new fine of {fine_amount:.2f} for currently overdue borrow record {db_borrow_record.id}.")
            
            # --- Commit and Sync if anything changed ---
            if status_changed or fine_changed:
                db.commit()
                manager = SyncManager(source_db=db_key)

                if status_changed:
                    logger.info(f"Borrow record {db_borrow_record.id} for user {db_borrow_record.user_id} and book {db_borrow_record.book_id} marked overdue. Due at: {db_borrow_record.due_at}, Current time: {current_time}.")
                    db.refresh(db_borrow_record)
                    manager.sync_instance(db_borrow_record)
                
                if fine_instance_to_sync:
                    db.refresh(fine_instance_to_sync)
                    manager.sync_instance(fine_instance_to_sync)
            
            updated_count += 1
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating overdue borrow record {db_borrow_record.id}: {e}")
            
    return updated_count


def get_user_all_reservations(db: Session, user_id: int) -> List[models.SeatReservation]:
    """Retrieves all seat reservations for a given user, ordered by reserved_at descending."""
    return list(db.execute(
        select(models.SeatReservation)
        .where(models.SeatReservation.user_id == user_id)
        .order_by(models.SeatReservation.reserved_at.desc())
    ).scalars())


# ---------------------------------------------------------------------------
# Reporting utilities
# ---------------------------------------------------------------------------

def compute_dashboard(db: Session, user: models.User) -> schemas.DashboardData:
    """
    Computes dashboard statistics.
    - User-specific stats are filtered by the provided user.
    - Global stats (total books, popular books) are for the whole system.
    """
    # ---------------------------------------------------------------------------
    # Global stats (for all users)
    # ---------------------------------------------------------------------------
    total_books = db.scalar(select(func.count(models.Book.id))) or 0

    popular_books_query = (
        select(models.Book.id, models.Book.title, func.count(models.BorrowRecord.id).label("borrow_count"))
        .join(models.BorrowRecord, models.Book.id == models.BorrowRecord.book_id, isouter=True)
        .group_by(models.Book.id, models.Book.title)
        .order_by(func.count(models.BorrowRecord.id).desc())
        .limit(5)
    )
    popular_books = [
        schemas.PopularBook(book_id=row.id, title=row.title, borrow_count=row.borrow_count or 0)
        for row in db.execute(popular_books_query)
    ]

    # ---------------------------------------------------------------------------
    # User-specific stats
    # ---------------------------------------------------------------------------
    borrowed_books = db.scalar(
        select(func.count(models.BorrowRecord.id)).where(
            models.BorrowRecord.user_id == user.id,
            models.BorrowRecord.returned_at == None
        )
    ) or 0
    overdue_loans = db.scalar(
        select(func.count(models.BorrowRecord.id)).where(
            models.BorrowRecord.user_id == user.id,
            models.BorrowRecord.due_at < datetime.utcnow(),
            models.BorrowRecord.returned_at == None
        )
    ) or 0
    fines_due = db.scalar(
        select(func.coalesce(func.sum(models.Fine.amount), 0)).where(
            models.Fine.user_id == user.id,
            models.Fine.paid == False
        )
    ) or 0.0
    active_reservations = db.scalar(
        select(func.count(models.SeatReservation.id)).where(
            models.SeatReservation.user_id == user.id,
            models.SeatReservation.status == "active"
        )
    ) or 0
    historical_overdue_records = db.scalar(
        select(func.count(models.BorrowRecord.id)).where(
            models.BorrowRecord.user_id == user.id,
            models.BorrowRecord.returned_at != None,
            models.BorrowRecord.returned_at > models.BorrowRecord.due_at
        )
    ) or 0

    # User's borrowing trend by week (last 4 weeks)
    trend: List[schemas.BorrowingTrendPoint] = []
    for weeks_ago in range(3, -1, -1):
        start = datetime.utcnow() - timedelta(weeks=weeks_ago + 1)
        end = datetime.utcnow() - timedelta(weeks=weeks_ago)
        count = db.scalar(
            select(func.count(models.BorrowRecord.id)).where(
                models.BorrowRecord.user_id == user.id,
                models.BorrowRecord.borrowed_at >= start,
                models.BorrowRecord.borrowed_at < end,
            )
        ) or 0
        trend.append(schemas.BorrowingTrendPoint(period=f"Week -{weeks_ago}", borrow_count=count))

    return schemas.DashboardData(
        summary=schemas.StatsSummary(
            total_books=total_books,
            borrowed_books=borrowed_books,
            overdue_loans=overdue_loans,
            historical_overdue_records=historical_overdue_records,
            fines_due=float(fines_due),
            active_reservations=active_reservations,
        ),
        borrowing_trend=trend,
        popular_books=popular_books,
    )


def get_system_stats(db: Session) -> schemas.SystemStats:
    total_borrowed_books = db.scalar(
        select(func.count(models.BorrowRecord.id)).where(models.BorrowRecord.returned_at == None)
    ) or 0

    # Historical overdue includes returned-late and currently-overdue
    returned_late = db.scalar(
        select(func.count(models.BorrowRecord.id)).where(
            models.BorrowRecord.returned_at != None,
            models.BorrowRecord.returned_at > models.BorrowRecord.due_at
        )
    ) or 0
    currently_overdue = db.scalar(
        select(func.count(models.BorrowRecord.id)).where(
            models.BorrowRecord.due_at < datetime.utcnow(), models.BorrowRecord.returned_at == None
        )
    ) or 0
    historical_overdue_count = returned_late + currently_overdue

    active_seat_reservations = db.scalar(
        select(func.count(models.SeatReservation.id)).where(models.SeatReservation.status == "active")
    ) or 0
    total_book_titles = db.scalar(select(func.count(models.Book.id))) or 0
    total_book_copies = db.scalar(select(func.sum(models.Book.total_copies))) or 0

    return schemas.SystemStats(
        total_borrowed_books=total_borrowed_books,
        historical_overdue_count=historical_overdue_count,
        active_seat_reservations=active_seat_reservations,
        total_book_titles=total_book_titles,
        total_book_copies=total_book_copies,
    )


# ---------------------------------------------------------------------------
# System Settings
# ---------------------------------------------------------------------------

def get_setting(db: Session, key: str) -> Optional[models.SystemSetting]:
    return db.execute(select(models.SystemSetting).where(models.SystemSetting.key == key)).scalar_one_or_none()


def set_setting(db: Session, key: str, value: str, db_key: str) -> models.SystemSetting:
    db_setting = get_setting(db, key)
    if db_setting:
        pre_modification_check(models.SystemSetting, db_setting.id, db_key)
        db_setting.value = value
    else:
        db_setting = models.SystemSetting(key=key, value=value)
        db.add(db_setting)
    
    db.commit()
    db.refresh(db_setting)
    manager = SyncManager(source_db=db_key)
    manager.sync_instance(db_setting)
    return db_setting


def list_settings(db: Session) -> List[models.SystemSetting]:
    return list(db.execute(select(models.SystemSetting)).scalars())
# ---------------------------------------------------------------------------
# Data Conflicts
# ---------------------------------------------------------------------------
def create_data_conflict(db: Session, conflict: schemas.DataConflictCreate) -> models.DataConflict:
    """Creates a new data conflict record."""
    db_conflict = models.DataConflict(**conflict.dict())
    db.add(db_conflict)
    db.commit()
    db.refresh(db_conflict)
    return db_conflict

def get_unresolved_conflicts(db: Session) -> List[models.DataConflict]:
    """Retrieves a list of all unresolved data conflicts."""
    return list(db.execute(
        select(models.DataConflict)
        .where(models.DataConflict.status == "unresolved")
        .order_by(models.DataConflict.created_at.desc())
    ).scalars())

def get_conflict_by_id(db: Session, conflict_id: int) -> Optional[models.DataConflict]:
    """Retrieves a data conflict by its ID."""
    return db.get(models.DataConflict, conflict_id)


def resolve_conflict(db: Session, conflict_id: int, resolution: schemas.DataConflictUpdate, db_key: str) -> models.DataConflict:
    """
    Resolves a data conflict by updating the record with the chosen data from one of the conflicting databases
    and marking the conflict as resolved. The resolved state is then force-synced to all other databases.
    """
    db_conflict = get_conflict_by_id(db, conflict_id)
    if not db_conflict:
        raise ValueError("Conflict not found")

    if db_conflict.status != "unresolved":
        raise ValueError("Conflict has already been resolved")

    resolution_key = resolution.resolution_db_key
    if resolution_key not in db_conflict.conflicting_data:
        raise ValueError(f"Invalid resolution key: '{resolution_key}'. Must be one of {list(db_conflict.conflicting_data.keys())}")

    chosen_data = db_conflict.conflicting_data[resolution_key]
    if not chosen_data:
        raise ValueError(f"Chosen data for resolution key '{resolution_key}' is empty")

    # Dynamically get the model class from the table name
    model_class = next(
        (mapper.class_ for mapper in models.Base.registry.mappers if mapper.local_table.name == db_conflict.table_name),
        None
    )
    if not model_class:
        raise ValueError(f"Model class for table '{db_conflict.table_name}' not found")

    # The `db` session is from the primary database ('main')
    record_to_update = db.get(model_class, db_conflict.record_id)
    if not record_to_update:
        # This can happen if the record was deleted on 'main' but the conflict remains.
        # We need to recreate it based on the chosen data.
        # Note: This assumes the chosen_data contains all necessary fields for creation.
        record_to_update = model_class(**chosen_data)
        db.add(record_to_update)
        logger.info(f"Record {db_conflict.record_id} not found in primary DB, recreating from resolved data.")
    else:
        # Update existing record
        for key, value in chosen_data.items():
            if hasattr(record_to_update, key):
                # Handle datetime string conversion
                if isinstance(getattr(record_to_update.__class__, key).property.columns[0].type, (
                    sqlalchemy.DateTime, sqlalchemy.Date, sqlalchemy.Time
                )) and isinstance(value, str):
                    try:
                        # Attempt to parse ISO 8601 format strings
                        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse date string '{value}' for {key}, leaving as is.")
                        pass # Keep original string if parsing fails

                setattr(record_to_update, key, value)

    # Mark the conflict as resolved
    db_conflict.status = f"resolved_{resolution_key}"
    db_conflict.resolved_at = datetime.utcnow()

    # Also update all original SyncLog entries that reported this conflict
    sync_log_entries = db.query(models.SyncLog).filter(models.SyncLog.conflict_id == db_conflict.id).all()
    for sync_log_entry in sync_log_entries:
        sync_log_entry.status = "resolved"
        sync_log_entry.details = f"Conflict resolved by choosing data from '{resolution_key}'. Record forced-synced to all replicas."
    
    db.commit()

    db.refresh(record_to_update)
    db.refresh(db_conflict)

    # Now, force sync the resolved state to all replicas
    manager = SyncManager(source_db=resolution.source_db) # db_key should be 'main' when called from API
    manager.sync_instance(record_to_update, force_update=True, suppress_logging=True)
    manager.sync_instance(db_conflict, force_update=True, suppress_logging=True)

    return db_conflict

def get_sync_stats_summary(days: int = 7, dbs: Optional[List[str]] = None) -> schemas.SyncStatsSummary:
    """
    Calculates synchronization statistics for the last N days and a summary of errors by table,
    aggregating data from all configured databases.
    """
    start_date = datetime.utcnow().date() - timedelta(days=days)

    all_daily_results = []
    all_conflict_results = []
    all_error_summary_results = []
    total_unresolved_conflicts = 0
    total_resolved_conflicts = 0

    db_keys_to_query = dbs if dbs else SessionFactories.keys()

    for db_key in db_keys_to_query:
        if db_key not in SessionFactories:
            continue
        session_factory = SessionFactories[db_key]
        with session_factory() as session:
            # Daily stats query
            log_date = func.cast(models.SyncLog.logged_at, sqlalchemy.Date).label("log_date")
            daily_stats_query = (
                select(
                    log_date,
                    func.count(models.SyncLog.id).label("total"),
                    func.sum(case((models.SyncLog.status == "failed", 1), else_=0)).label("failures")
                )
                .where(models.SyncLog.logged_at >= start_date)
                .group_by(log_date)
            )
            all_daily_results.extend(session.execute(daily_stats_query).all())

            # Conflict counts query
            conflict_date_label = func.cast(models.SyncLog.logged_at, sqlalchemy.Date).label("conflict_date")
            unique_daily_conflicts_sq = (
                select(conflict_date_label, models.SyncLog.conflict_id)
                .where(models.SyncLog.logged_at >= start_date, models.SyncLog.conflict_id != None)
                .group_by(conflict_date_label, models.SyncLog.conflict_id)
            ).alias("unique_daily_conflicts")
            
            conflict_counts_query = (
                select(
                    unique_daily_conflicts_sq.c.conflict_date,
                    func.sum(case((models.DataConflict.status.like("resolved_%"), 1), else_=0)).label("resolved_conflicts"),
                    func.sum(case((models.DataConflict.status == "unresolved", 1), else_=0)).label("unresolved_conflicts")
                )
                .join(models.DataConflict, unique_daily_conflicts_sq.c.conflict_id == models.DataConflict.id)
                .group_by(unique_daily_conflicts_sq.c.conflict_date)
            )
            all_conflict_results.extend(session.execute(conflict_counts_query).all())
            
            # Error summary query
            error_summary_query = (
                select(
                    models.SyncLog.table_name,
                    func.count(case((models.SyncLog.conflict_id != None, 1))).label("conflict_count"),
                    func.count(case((models.SyncLog.status == "failed", 1))).label("failure_count")
                )
                .where((models.SyncLog.conflict_id != None) | (models.SyncLog.status == "failed"))
                .group_by(models.SyncLog.table_name)
            )
            all_error_summary_results.extend(session.execute(error_summary_query).all())
            
            # Overall conflict counts from the primary MySQL database, which is the authority
            if db_key == "MySQL":
                total_unresolved_conflicts = session.scalar(select(func.count(models.DataConflict.id)).where(models.DataConflict.status == "unresolved")) or 0
                total_resolved_conflicts = session.scalar(select(func.count(models.DataConflict.id)).where(models.DataConflict.status.like("resolved_%"))) or 0

    # --- Aggregation ---
    
    # Aggregate daily stats
    daily_map = defaultdict(lambda: {"total": 0, "failures": 0})
    for row in all_daily_results:
        # Ensure row.log_date is a date object, not a string
        log_date_obj = row.log_date
        if isinstance(log_date_obj, str):
            log_date_obj = date.fromisoformat(log_date_obj)
        daily_map[log_date_obj]["total"] += row.total
        daily_map[log_date_obj]["failures"] += row.failures
        
    # Aggregate conflict stats
    conflict_map = defaultdict(lambda: {"resolved_conflicts": 0, "unresolved_conflicts": 0})
    for row in all_conflict_results:
        # Ensure row.conflict_date is a date object
        conflict_date_obj = row.conflict_date
        if isinstance(conflict_date_obj, str):
            conflict_date_obj = date.fromisoformat(conflict_date_obj)
        conflict_map[conflict_date_obj]["resolved_conflicts"] += row.resolved_conflicts
        conflict_map[conflict_date_obj]["unresolved_conflicts"] += row.unresolved_conflicts

    # Generate canonical list of dates and populate stats
    date_range = [start_date + timedelta(days=i) for i in range(days + 1)]
    daily_stats_list = []
    for day in date_range:
        data = daily_map.get(day)
        conflict_data = conflict_map.get(day)
        
        resolved = conflict_data["resolved_conflicts"] if conflict_data else 0
        unresolved = conflict_data["unresolved_conflicts"] if conflict_data else 0

        daily_stats_list.append(schemas.SyncStatsByDay(
            date=day.isoformat(),
            total_operations=data["total"] if data else 0,
            conflicts=resolved + unresolved,
            failures=data["failures"] if data else 0,
            resolved_conflicts=resolved,
            unresolved_conflicts=unresolved,
        ))
        
    # Aggregate error summary by table
    error_summary_map = defaultdict(lambda: {"conflict_count": 0, "failure_count": 0})
    for row in all_error_summary_results:
        error_summary_map[row.table_name]["conflict_count"] += row.conflict_count
        error_summary_map[row.table_name]["failure_count"] += row.failure_count

    error_summary_list = [
        schemas.SyncErrorsByTable(
            table_name=table,
            conflict_count=counts["conflict_count"],
            failure_count=counts["failure_count"],
        ) for table, counts in sorted(error_summary_map.items())
    ]
    
    # Overall stats
    total_operations = sum(s.total_operations for s in daily_stats_list)
    total_conflicts = sum(s.conflicts for s in daily_stats_list)
    total_failures = sum(s.failures for s in daily_stats_list)
    
    overall_stats = schemas.OverallSyncStats(
        total_operations=total_operations,
        successful_syncs=total_operations - total_conflicts - total_failures,
        total_conflicts=total_conflicts,
        total_failures=total_failures,
        unresolved_conflicts=total_unresolved_conflicts,
        resolved_conflicts=total_resolved_conflicts,
    )

    return schemas.SyncStatsSummary(
        daily_stats=daily_stats_list,
        error_summary_by_table=error_summary_list,
        overall_stats=overall_stats,
    )