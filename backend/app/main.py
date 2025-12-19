"""FastAPI application exposing the library management APIs."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List
import itertools
import operator
import asyncio # New import
import time # New import
import logging # Added import
# import sys # REMOVED IMPORT

from .compat import patch_forward_ref_for_py312

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

# Configure logging using basicConfig, which is often more compatible with uvicorn
logging.basicConfig(level=logging.DEBUG)


from . import crud, models, schemas
from .database import init_databases, SessionFactories
from .dependencies import get_current_user, ensure_admin, get_db_dependency, get_db_key_dependency
from .config import (
    OVERDUE_RESERVATION_CHECK_INTERVAL_KEY,
    DEFAULT_OVERDUE_RESERVATION_CHECK_INTERVAL,
    OVERDUE_BORROW_GRACE_PERIOD_KEY, # New import for config
    DEFAULT_OVERDUE_BORROW_GRACE_PERIOD # New import for config
)

from .routers import user, books, seats, borrow, dashboard, settings, conflicts, stats # Ensure router imports are here


# register FastAPI app
app = FastAPI(
    title="Library Management System",
    description="支持多数据库同步的后端系统",
    version="0.1.0"
)

patch_forward_ref_for_py312()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def run_system_maintenance_tasks():
    """
    Background task to periodically check for and update various time-sensitive records
    like overdue seat reservations and overdue borrow records.
    The check interval is configurable via system settings.
    """
    while True:
        # Get the current interval from settings, default to 20 seconds
        interval = DEFAULT_OVERDUE_RESERVATION_CHECK_INTERVAL
        
        db_key_for_settings = next(iter(SessionFactories.keys()))
        with SessionFactories[db_key_for_settings]() as db:
            setting = crud.get_setting(db, OVERDUE_RESERVATION_CHECK_INTERVAL_KEY)
            if setting and setting.value.isdigit():
                interval = max(1, int(setting.value)) # Ensure interval is at least 1 second

        print(f"Running system maintenance tasks (interval: {interval}s)...")
        for db_key in SessionFactories:
            with SessionFactories[db_key]() as db:
                try:
                    defaulted_reservations_count = crud.default_overdue_reservations(db, db_key=db_key)
                    if defaulted_reservations_count > 0:
                        print(f"Defaulted {defaulted_reservations_count} overdue reservations in {db_key}.")
                except Exception as e:
                    print(f"Error in overdue reservation task for {db_key}: {e}")

                try:
                    overdue_borrows_count = crud.default_overdue_borrow_records(db, db_key=db_key)
                    if overdue_borrows_count > 0:
                        print(f"Updated {overdue_borrows_count} overdue borrow records in {db_key}.")
                except Exception as e:
                    print(f"Error in overdue borrow records task for {db_key}: {e}")

        await asyncio.sleep(interval)

@app.on_event("startup")
def on_startup() -> None:
    init_databases()
    asyncio.create_task(run_system_maintenance_tasks()) # Start the background task

app.include_router(user.router)
app.include_router(books.router)
app.include_router(seats.router)
app.include_router(borrow.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(conflicts.router)
app.include_router(conflicts.public_router)
app.include_router(stats.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Library Management System!"}

# ---------------------------------------------------------------------------
# Dashboard & sync logs
# ---------------------------------------------------------------------------

@app.get("/dashboard", response_model=schemas.DashboardData)
def dashboard(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db_dependency)):
    return crud.compute_dashboard(db)


@app.get("/sync/logs", response_model=List[schemas.GroupedSyncLogRead])
def read_sync_logs(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db_key_dependency),
):
    """
    Returns a list of synchronization logs from ALL databases, grouped by the source event.
    """
    ensure_admin(current_user)
    
    master_log_list: List[models.SyncLog] = []
    
    # 1. Fetch logs from all databases. The logs are written on the *source* database of the sync.
    for db_key in SessionFactories:
        session = SessionFactories[db_key]()
        try:
            logs = session.query(models.SyncLog).filter(models.SyncLog.source_db == db_key).all()
            master_log_list.extend(logs)
        finally:
            session.close()

    # 2. Sort the master list by time globally
    master_log_list.sort(key=operator.attrgetter("logged_at"), reverse=True)

    grouped_logs: List[schemas.GroupedSyncLogRead] = []
    processed_events = set()

    # 3. Group the globally sorted logs by event
    for log_item in master_log_list:
        time_bucket = int(log_item.logged_at.timestamp() / 2) # Group events in 2-second windows
        processing_key = (log_item.source_db, log_item.table_name, log_item.record_id, time_bucket)

        if processing_key in processed_events:
            continue
        
        # Find all other logs that are part of this same source event
        source_event_logs = [
            log for log in master_log_list
            if log.source_db == log_item.source_db
            and log.table_name == log_item.table_name
            and log.record_id == log_item.record_id
            and abs(log.logged_at.timestamp() - log_item.logged_at.timestamp()) < 2
        ]
        
        if not source_event_logs:
            continue

        # Mark all logs in this event cluster as processed
        for log in source_event_logs:
            p_key = (log.source_db, log.table_name, log.record_id, int(log.logged_at.timestamp() / 2))
            processed_events.add(p_key)

        first_log = source_event_logs[0]

        # Collect all unique conflict_ids within this group
        group_conflict_ids = {log.conflict_id for log in source_event_logs if log.conflict_id}
        
        # Fetch the status of all relevant DataConflicts from the MAIN database
        resolved_conflict_statuses = {}  # {conflict_id: "resolved" or "unresolved"}
        if group_conflict_ids:
            # ALWAYS check the 'main' database for the authoritative conflict status
            with SessionFactories[db]() as main_db_session:
                for conflict_id in group_conflict_ids:
                    # Use the main_db_session to get the conflict
                    data_conflict = crud.get_conflict_by_id(main_db_session, conflict_id)
                    if data_conflict:
                        if data_conflict.status.startswith("resolved_"):
                            resolved_conflict_statuses[conflict_id] = "resolved"
                        else:
                            resolved_conflict_statuses[conflict_id] = "unresolved"


        replicas = []
        for log in source_event_logs:
            display_status = log.status # Default to the log's original status

            if log.conflict_id and log.conflict_id in resolved_conflict_statuses:
                # Override status based on DataConflict's actual status
                display_status = resolved_conflict_statuses[log.conflict_id]
            
            # Note: If log.status is 'conflict' but no conflict_id, it stays 'conflict'.
            # This is correct as it represents an unmanaged conflict.
            # If log.status is 'failed', it stays 'failed' unless overridden by a resolved conflict_id

            replicas.append(
                schemas.SyncLogReplicaDetail(
                    target_db=log.target_db,
                    status=display_status,
                    details=log.details,
                    conflict_id=log.conflict_id
                )
            )
        
        grouped_logs.append(
            schemas.GroupedSyncLogRead(
                key=f"{first_log.source_db}-{first_log.table_name}-{first_log.record_id}-{first_log.logged_at.isoformat()}",
                source_db=first_log.source_db,
                table_name=first_log.table_name,
                record_id=first_log.record_id,
                logged_at=first_log.logged_at,
                replicas=replicas
            )
        )

    return grouped_logs[:100]


# ---------------------------------------------------------------------------
# Utility endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok", "time": datetime.utcnow().isoformat()}