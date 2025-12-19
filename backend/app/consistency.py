from __future__ import annotations

from typing import Type, Dict, Any
from decimal import Decimal
from sqlalchemy.inspection import inspect
from datetime import datetime

from .database import get_session, DATABASE_URLS
from . import models, schemas, crud
from .sync_manager import SyncManager


def get_instances_from_all_dbs(model_class: Type[models.Base], record_id: int) -> dict[str, models.Base | None]:
    """Fetches an instance of a model by its ID from all configured databases."""
    instances = {}
    for db_key in DATABASE_URLS.keys():
        with get_session(db_key) as session:
            instance = session.get(model_class, record_id)
            instances[db_key] = instance
    return instances


def _as_dict(instance: models.Base) -> Dict[str, Any]:
    """Converts a SQLAlchemy model instance to a dictionary, handling datetime."""
    if not instance:
        return {}
    mapper = inspect(instance).mapper
    data = {}
    for column in mapper.column_attrs:
        value = getattr(instance, column.key)
        # For consistency in comparison, convert datetimes to a standard string format.
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = float(value)
        data[column.key] = value
    return data


def pre_modification_check(model_class: Type[models.Base], record_id: int, source_db: str):
    """
    Checks data consistency for a given record across all databases before a modification.

    - Fetches the record from all databases.
    - Compares their state.
    - If inconsistent, it logs the conflict, sends an email to admins, and then raises a ValueError.
    """
    if record_id is None:
        return

    instances = get_instances_from_all_dbs(model_class, record_id)
    db_keys = list(instances.keys())

    if len(db_keys) < 2:
        return  # Nothing to compare

    # Convert all instances to dicts for comparison and storage
    all_instance_dicts = {db_key: _as_dict(instance) for db_key, instance in instances.items()}

    # Check for consistency across all instances
    is_consistent = True
    first_dict = None
    for db_key in db_keys:
        current_dict = all_instance_dicts[db_key]
        if first_dict is None:
            first_dict = current_dict
        elif first_dict != current_dict:
            is_consistent = False
            break # Found an inconsistency

    if not is_consistent:
        # Inconsistency found. Log it, notify admins, and abort the operation.
        with get_session(source_db) as session: # Use the source_db session to log the conflict
            conflict_create = schemas.DataConflictCreate(
                table_name=model_class.__tablename__,
                record_id=record_id,
                conflicting_data=all_instance_dicts, # Store all versions
                status="unresolved",
            )
            new_conflict = crud.create_data_conflict(db=session, conflict=conflict_create)

            # =================================================================
            # 将“未解决”的冲突记录同步到所有数据库
            # =================================================================
            try:
                # 初始化 SyncManager，源数据库为当前发现冲突的库
                manager = SyncManager(source_db=source_db)
                
                # 强制同步这个 DataConflict 对象到其他从库
                # 这样无论管理员登录哪个数据库，都能看到这条冲突详情
                manager.sync_instance(new_conflict)
                
                # 注意：这里不需要 catch 异常，因为 sync_instance 内部已经处理了 try-except
            except Exception as e:
                # 仅仅是为了防御性编程，防止同步冲突记录失败导致主流程报错
                # 实际上 sync_manager 内部有日志记录
                print(f"Warning: Failed to sync conflict record to other DBs: {e}")
            # =================================================================
            
            # Also create a SyncLog entry and send notification via the SyncManager
            if 'manager' not in locals():
                manager = SyncManager(source_db=source_db)
                
            manager._record_log(
                table_name=model_class.__tablename__,
                record_id=record_id,
                replica="multi-party", # Indicate a multi-party conflict
                status="conflict",
                details=f"Pre-modification check found multi-party inconsistency. Conflict ID: {new_conflict.id}",
                conflict_id=new_conflict.id,
            )

            # Call the centralized email function
            manager._send_conflict_email(
                session,
                table_name=model_class.__tablename__,
                record_id=record_id,
                conflict_id=new_conflict.id,
            )

        raise ValueError(
            f"Multi-party data inconsistency detected for {model_class.__tablename__} #{record_id}. "
            f"Operation aborted and conflict logged (ID: {new_conflict.id}). An email has been sent to administrators."
        )