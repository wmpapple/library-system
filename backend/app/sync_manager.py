"""Utilities to keep databases in sync and record conflicts."""
from __future__ import annotations

import json
from decimal import Decimal
import logging # Added import
from datetime import datetime
from pathlib import Path
from typing import Iterable, Type

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.inspection import inspect

from . import models
from .database import ENGINES, get_session

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "sync.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__) # NEW LOGGER INITIALIZATION


class SyncManager:
    """Synchronise SQLAlchemy models across replica databases."""

    timestamp_fields = (
        "updated_at",
        "last_modified",
        "calculated_at",
        "reserved_at",
        "borrowed_at",
        "created_at",
    )

    def __init__(self, source_db: str = "primary") -> None:
        self.source_db = source_db
        self.replicas = [name for name in ENGINES.keys() if name != source_db]

    # ------------------------------------------------------------------
    # public helpers
    # ------------------------------------------------------------------
    def sync_instance(self, instance: models.Base, table_name: str | None = None, force_update: bool = False, suppress_logging: bool = False) -> None:
        """
        Synchronise ``instance`` to every configured replica database.
        Conflict detection is handled before this method is called.
        """
        model_class: Type[models.Base] = type(instance)
        table_name = table_name or model_class.__tablename__
        payload = self._as_dict(instance)

        for replica in self.replicas:
            status = "synced"
            details = f"Data synced: {json.dumps(payload, ensure_ascii=False, indent=2)}"
            try:
                with get_session(replica) as session:
                    existing = session.get(model_class, payload["id"])
                    if existing:
                        # Pre-modification checks are now responsible for consistency.
                        # We just apply the changes.
                        for key, value in payload.items():
                            setattr(existing, key, value)
                    else:
                        # If the record doesn't exist on the replica, create it.
                        session.add(model_class(**payload))
            except SQLAlchemyError as exc:  # pragma: no cover - best effort logging
                status = "failed"
                details = str(exc)
            
            if not suppress_logging:
                # We pass a null conflict_id as this method no longer detects conflicts.
                self._record_log(table_name, payload["id"], replica, status, details, conflict_id=None)
            logger.info(f"[SyncManager] Synced '{table_name}' ID {payload['id']} to replica '{replica}' with status: {status}.")

    def delete_instance(self, model_class: Type[models.Base], record_id: int) -> None:
        """Remove the record from replica databases."""
        table_name = model_class.__tablename__
        for replica in self.replicas:
            status = "deleted"
            details = f"Record with ID {record_id} deleted from table {table_name}."
            try:
                with get_session(replica) as session:
                    target = session.get(model_class, record_id)
                    if target:
                        session.delete(target)
            except SQLAlchemyError as exc:  # pragma: no cover
                status = "failed"
                details = str(exc)
            self._record_log(table_name, record_id, replica, status, details)
            logger.info(f"[SyncManager] Deleted '{table_name}' ID {record_id} from replica '{replica}' with status: {status}.")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _as_dict(self, instance: models.Base) -> dict:
        """Converts a SQLAlchemy model instance to a dictionary, handling datetime."""
        if not instance:
            return {}
        mapper = inspect(instance).mapper
        data = {}
        for column in mapper.column_attrs:
            value = getattr(instance, column.key)
            if isinstance(value, datetime):
                value = value.isoformat()
            # 处理 Decimal (新增)
            elif isinstance(value, Decimal):
                value = float(value)
            data[column.key] = value
        return data

    def _last_modified(self, instance: models.Base) -> datetime | None:
        for field in self.timestamp_fields:
            if hasattr(instance, field):
                value = getattr(instance, field)
                if isinstance(value, datetime):
                    return value
        return None

    def _record_log(
        self,
        table_name: str,
        record_id: int,
        replica: str,
        status: str,
        details: str | None,
        conflict_id: int | None = None,
    ) -> None:
        with get_session(self.source_db) as session:
            log_entry = models.SyncLog(
                source_db=self.source_db,
                target_db=replica,
                table_name=table_name,
                record_id=record_id,
                status=status,
                details=details,
                conflict_id=conflict_id,
            )
            session.add(log_entry)

    def _send_conflict_email(
        self,
        session: Session,
        *,
        table_name: str,
        record_id: int,
        conflict_id: int,
        conflicting_data: dict[str, any],
        notification_type: str,
    ):
        """
        Sends a standardized email notification for a data conflict.
        
        :param session: The SQLAlchemy session to use for querying admin users.
        :param table_name: The name of the table with the conflict.
        :param record_id: The ID of the conflicting record.
        :param conflict_id: The ID of the DataConflict entry.
        :param conflicting_data: A dictionary containing the different versions of the data.
        :param notification_type: A string describing when the conflict was detected (e.g., "pre-modification").
        """
        import json
        from . import config, crud
        from .email import send_email

        subject = f"URGENT: Data Conflict Detected in {table_name}"
        pretty_conflicts = json.dumps(conflicting_data, indent=2, ensure_ascii=False)

        if notification_type == "pre-modification":
            intro = "A data conflict was detected during a pre-modification check, and the requested operation was automatically aborted."
        else:  # "post-sync"
            intro = "A data conflict was detected during data synchronization."

        body = (
            f"{intro}\n\n"
            f"Table: {table_name}\n"
            f"Record ID: {record_id}\n"
            f"Conflict ID: {conflict_id}\n\n"
            f"The following conflicting data was found across the databases:\n\n{pretty_conflicts}\n\n"
            f"Please log in to the admin panel to resolve this conflict."
        )

        admin_emails = set()
        try:
            admins = crud.get_admin_users(session)
            for admin in admins:
                if admin.email:
                    admin_emails.add(admin.email)
        except Exception as e:
            logger.error(f"Error getting admin users for conflict email notification: {e}")

        for email in filter(None, admin_emails):
            send_email(email_to=email, subject=subject, body=body)


sync_manager = SyncManager()
