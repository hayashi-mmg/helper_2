from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_assignments,
    admin_compliance,
    admin_data_access_logs,
    admin_menus,
    admin_system,
    admin_users,
    auth,
    menus,
    messages,
    pantry,
    qr,
    recipe_ingredients,
    recipes,
    shopping,
    tasks,
    telemetry,
    themes,
    users,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(recipe_ingredients.router)
api_router.include_router(recipes.router)
api_router.include_router(menus.router)
api_router.include_router(tasks.router)
api_router.include_router(messages.router)
api_router.include_router(shopping.router)
api_router.include_router(pantry.router)
api_router.include_router(qr.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_assignments.router)
api_router.include_router(admin_menus.router)
# themes を admin_system より先に登録することで、
# /admin/settings/default_theme_id の専用ハンドラが汎用ハンドラより優先される。
api_router.include_router(themes.router)
api_router.include_router(admin_system.router)
api_router.include_router(admin_data_access_logs.router)
api_router.include_router(admin_compliance.router)
api_router.include_router(telemetry.router)
