"""The JSON API. The OpenAPI document is not served: `manage.py export_openapi_schema` writes
it for the frontend's generated client (see frontend/orval.config.ts)."""
from ninja import NinjaAPI

from accounts.api import router as accounts_router
from ops.api import router as ops_router

api = NinjaAPI(title="Nurse roster", version="1", openapi_url=None, docs_url=None)
api.add_router("", ops_router)
api.add_router("/auth", accounts_router)
