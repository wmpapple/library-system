"""SQLAlchemy models for the library management system."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, Text, JSON, Unicode
from sqlalchemy.dialects import mysql, mssql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# Define a custom type that supports microsecond precision on all dialects
Timestamp = DateTime(timezone=False).with_variant(mysql.DATETIME(fsp=6), "mysql").with_variant(mssql.DATETIME2(precision=6), "mssql")


class RoleEnum(str, Enum):  # type: ignore[misc]
    ADMIN = "admin"
    STUDENT = "student"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(Unicode(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Unicode(128), nullable=False)
    role: Mapped[str] = mapped_column(Unicode(20), default=RoleEnum.STUDENT.value)
    email: Mapped[Optional[str]] = mapped_column(Unicode(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=datetime.utcnow)

    borrow_records: Mapped[List["BorrowRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    fines: Mapped[List["Fine"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reservations: Mapped[List["SeatReservation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    author: Mapped[str] = mapped_column(Unicode(120), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(Unicode(120))
    isbn: Mapped[str] = mapped_column(Unicode(30), unique=True, nullable=False)
    total_copies: Mapped[int] = mapped_column(Integer, default=1)
    available_copies: Mapped[int] = mapped_column(Integer, default=1)
    rating: Mapped[Optional[float]] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(
        Timestamp, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    borrow_records: Mapped[List["BorrowRecord"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )


class BorrowRecord(Base):
    __tablename__ = "borrow_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    borrowed_at: Mapped[datetime] = mapped_column(Timestamp, default=datetime.utcnow)
    due_at: Mapped[datetime] = mapped_column(Timestamp, nullable=False)
    returned_at: Mapped[Optional[datetime]] = mapped_column(Timestamp, nullable=True)
    status: Mapped[str] = mapped_column(Unicode(20), default="borrowed")
    last_modified: Mapped[datetime] = mapped_column(Timestamp, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="borrow_records")
    book: Mapped[Book] = relationship(back_populates="borrow_records")
    fine: Mapped[Optional["Fine"]] = relationship(back_populates="borrow_record") # New relationship


class Fine(Base):
    __tablename__ = "fines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    borrow_record_id: Mapped[int] = mapped_column(ForeignKey("borrow_records.id"), unique=True, nullable=False) # Link to borrow record
    amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    calculated_at: Mapped[datetime] = mapped_column(Timestamp, default=datetime.utcnow)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="fines")
    borrow_record: Mapped["BorrowRecord"] = relationship(back_populates="fine") # Add relationship



class Seat(Base):
    __tablename__ = "seats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    floor: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    code: Mapped[str] = mapped_column(Unicode(20), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(Unicode(20), default="available")

    reservations: Mapped[List["SeatReservation"]] = relationship(
        back_populates="seat", cascade="all, delete-orphan"
    )


class SeatReservation(Base):
    __tablename__ = "seat_reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"))
    reserved_at: Mapped[datetime] = mapped_column(Timestamp, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(Timestamp, nullable=False)
    status: Mapped[str] = mapped_column(Unicode(20), default="active")
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(Timestamp, nullable=True)

    user: Mapped[User] = relationship(back_populates="reservations")
    seat: Mapped[Seat] = relationship(back_populates="reservations")


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_db: Mapped[str] = mapped_column(Unicode(50))
    target_db: Mapped[str] = mapped_column(Unicode(50))
    table_name: Mapped[str] = mapped_column(Unicode(50))
    record_id: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Unicode(30))
    details: Mapped[Optional[str]] = mapped_column(Text)
    logged_at: Mapped[datetime] = mapped_column(Timestamp, default=datetime.utcnow)
    conflict_id: Mapped[Optional[int]] = mapped_column(ForeignKey("data_conflicts.id"), nullable=True)

    conflict: Mapped[Optional["DataConflict"]] = relationship()


class DataConflict(Base):
    __tablename__ = "data_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    table_name: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # Stores data from all conflicting databases as a dictionary: {'db_key': {record_data}}
    conflicting_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Status can be "unresolved" or "resolved_{db_key}" indicating which DB's data was chosen
    status: Mapped[str] = mapped_column(Unicode(50), default="unresolved", nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(Timestamp, nullable=True)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=datetime.utcnow)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(Unicode(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        Timestamp, default=datetime.utcnow, onupdate=datetime.utcnow
    )