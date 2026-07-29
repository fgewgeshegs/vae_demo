"""Dashboard overview API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/overview", response_model=dict)
async def get_dashboard_overview(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return one consistent, read-only view of the learner's next action."""
    return await DashboardService.overview(db, current_user.id)
