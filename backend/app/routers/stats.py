from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from .. import crud, schemas
from ..dependencies import ensure_admin

router = APIRouter(
    prefix="/stats",
    tags=["statistics"],
    dependencies=[Depends(ensure_admin)],
)

@router.get("/sync-summary", response_model=schemas.SyncStatsSummary)
def get_sync_summary(
    days: Optional[int] = 7,
    dbs: Optional[List[str]] = Query(None)
):
    """
    Retrieve synchronization statistics for the last N days and
    a summary of errors by table.
    """
    return crud.get_sync_stats_summary(days=days, dbs=dbs)
