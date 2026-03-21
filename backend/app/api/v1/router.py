from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.admin_users import router as admin_users_router
from app.api.v1.routes.case_gen import router as case_gen_router
from app.api.v1.routes.case_management import router as case_management_router
from app.api.v1.routes.system import router as system_router
from app.api.v1.routes.ui_automation import router as ui_automation_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
api_router.include_router(admin_users_router, prefix="/api/v1", tags=["admin"])
api_router.include_router(system_router, prefix="/api/v1/system", tags=["system"])
api_router.include_router(case_gen_router, prefix="/api/v1/case-gen", tags=["case-gen"])
api_router.include_router(case_management_router, prefix="/api/v1/case-management", tags=["case-management"])
api_router.include_router(ui_automation_router, prefix="/api/v1/ui-automation", tags=["ui-automation"])

