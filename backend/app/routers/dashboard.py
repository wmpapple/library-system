from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, crud, schemas
from ..dependencies import get_current_user, get_db_dependency, ensure_admin

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"]
)

@router.get("/", response_model=schemas.DashboardData)
def get_dashboard_stats(
    db: Session = Depends(get_db_dependency),
    current_user: models.User = Depends(get_current_user)
):
    """
    Computes and returns the main dashboard statistics.
    
    This includes a summary of library stats and a list of the most popular books.
    """
    return crud.compute_dashboard(db, user=current_user)

@router.get("/system", response_model=schemas.SystemStats)
def get_system_dashboard_stats(
    db: Session = Depends(get_db_dependency),
    admin_user: models.User = Depends(ensure_admin)
):
    """
    Computes and returns system-wide dashboard statistics for administrators.
    """
    return crud.get_system_stats(db)
