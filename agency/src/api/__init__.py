from fastapi import APIRouter

from .routes import router as routes_router
from .vault_routes import router as vault_router

api_router = APIRouter()
api_router.include_router(routes_router)
api_router.include_router(vault_router)
from .routes_crm import router as crm_router
api_router.include_router(crm_router)

__all__ = ["api_router"]
