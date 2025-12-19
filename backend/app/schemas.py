"""Pydantic schemas used by the API."""
from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, EmailStr, Field, ConfigDict

# the data checking and validation is handled here

class RoleEnum(str, Enum):
    ADMIN = "admin"
    STUDENT = "student"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: str = RoleEnum.STUDENT


class UserCreate(UserBase):
    password: str = Field(..., min_length=4, max_length=128)
    admin_token: Optional[str] = None

class UserRead(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str
    db_key: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str  # username
    db_key: str


class BookBase(BaseModel):
    title: str
    author: str
    category: Optional[str] = None
    isbn: str
    total_copies: int = 1
    available_copies: int = 1
    rating: Optional[float] = None


class BookCreate(BookBase):
    pass


class BookRead(BookBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True


class BorrowRecordBase(BaseModel):
    user_id: int
    book_id: int
    due_at: datetime


class BorrowRecordCreate(BorrowRecordBase):
    pass


class BorrowRecordUpdate(BaseModel):
    returned_at: Optional[datetime] = None
    status: Optional[str] = None


class BorrowRecordRead(BorrowRecordBase):
    id: int
    borrowed_at: datetime
    returned_at: Optional[datetime]
    status: str
    fine: Optional[FineRead] # New field

    class Config:
        from_attributes = True

class BorrowBookRequest(BaseModel):
    book_id: int
    due_at: datetime


class FineBase(BaseModel):
    user_id: int
    borrow_record_id: int
    amount: float
    paid: bool = False


class FineCreate(FineBase):
    pass


class FineRead(FineBase):
    id: int
    calculated_at: datetime

    class Config:
        from_attributes = True

class FineUpdate(BaseModel): # New Schema for updating fine
    paid: bool


class SeatBase(BaseModel):
    floor: int
    code: str
    status: str = "available"


class SeatCreate(SeatBase):
    pass


class SeatRead(SeatBase):
    id: int

    class Config:
        from_attributes = True


class SeatReservationBase(BaseModel):
    user_id: int
    seat_id: int
    expires_at: datetime


class SeatReservationCreate(SeatReservationBase):
    pass


class SeatReservationRead(SeatReservationBase):
    id: int
    reserved_at: datetime
    status: str
    cancelled_at: Optional[datetime]

    class Config:
        from_attributes = True


class SeatStats(BaseModel):
    total_count: int
    max_seat_num: int


class SyncLogRead(BaseModel):
    id: int
    source_db: str
    target_db: str
    table_name: str
    record_id: int
    status: str
    details: Optional[str]
    logged_at: datetime
    conflict_id: Optional[int] = None

    class Config:
        from_attributes = True


class SyncLogReplicaDetail(BaseModel):
    target_db: str
    status: str
    details: Optional[str]
    conflict_id: Optional[int] = None


class GroupedSyncLogRead(BaseModel):
    key: str
    source_db: str
    table_name: str
    record_id: int
    logged_at: datetime
    replicas: List[SyncLogReplicaDetail]


class DataConflictBase(BaseModel):
    table_name: str
    record_id: int
    # Stores data from all conflicting databases as a dictionary: {'db_key': {record_data}}
    conflicting_data: Dict[str, Dict[str, Any]] = Field(...)
    status: str = Field("unresolved", max_length=50) # Increased max_length


class DataConflictCreate(DataConflictBase):
    pass


class DataConflictRead(DataConflictBase):
    id: int
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DataConflictUpdate(BaseModel):
    # For resolution, frontend will send the key of the database whose data should be used
    resolution_db_key: str
    source_db: str


class ConflictAccess(BaseModel):
    token: str
    password: str



class StatsSummary(BaseModel):
    total_books: int
    borrowed_books: int
    overdue_loans: int
    historical_overdue_records: int
    fines_due: float
    active_reservations: int


class BorrowingTrendPoint(BaseModel):
    period: str
    borrow_count: int


class PopularBook(BaseModel):
    book_id: int
    title: str
    borrow_count: int


class DashboardData(BaseModel):
    summary: StatsSummary
    borrowing_trend: List[BorrowingTrendPoint]
    popular_books: List[PopularBook]


class SystemStats(BaseModel):
    total_borrowed_books: int
    historical_overdue_count: int
    active_seat_reservations: int
    total_book_titles: int
    total_book_copies: int


# System Settings
class SystemSettingBase(BaseModel):
    key: str
    value: str


class SystemSettingCreate(SystemSettingBase):
    pass


class SystemSettingRead(SystemSettingBase):
    id: int
    updated_at: datetime

    class Config(ConfigDict):
        from_attributes = True


class SystemSettingUpdate(BaseModel):
    value: str

# --- Schemas for Sync Statistics ---

class SyncStatsByDay(BaseModel):
    """Statistics for sync operations on a single day."""
    date: date
    total_operations: int
    conflicts: int
    failures: int
    resolved_conflicts: int
    unresolved_conflicts: int

class SyncErrorsByTable(BaseModel):
    """Error statistics (conflicts and failures) aggregated by table name."""
    table_name: str
    conflict_count: int
    failure_count: int


class OverallSyncStats(BaseModel):
    """High-level aggregated statistics over the requested period."""
    total_operations: int
    successful_syncs: int
    total_conflicts: int
    total_failures: int
    unresolved_conflicts: int
    resolved_conflicts: int


class SyncStatsSummary(BaseModel):
    """The main response model for the sync statistics dashboard."""
    daily_stats: List[SyncStatsByDay]
    error_summary_by_table: List[SyncErrorsByTable]
    overall_stats: OverallSyncStats