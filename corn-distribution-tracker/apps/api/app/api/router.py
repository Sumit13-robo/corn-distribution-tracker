"""API router registry."""

from fastapi import APIRouter

from app.api.routes import (
    analytics,
    assignments,
    auth,
    campaigns,
    distributions,
    evidence,
    inventory,
    settings,
    sites,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(campaigns.router)
api_router.include_router(sites.router)
api_router.include_router(assignments.router)
api_router.include_router(inventory.router)
api_router.include_router(distributions.router)
api_router.include_router(evidence.router)
api_router.include_router(analytics.router)
api_router.include_router(settings.router)
